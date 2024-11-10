import gzip
import os
import warnings
from pprint import pprint

from django.apps import apps
from django.core import serializers
from django.core.management.base import BaseCommand, CommandError
from django.core.management.utils import parse_apps_and_model_labels
from django.db import DEFAULT_DB_ALIAS, connections, router

try:
    import bz2

    has_bz2 = True
except ImportError:
    has_bz2 = False

try:
    import lzma

    has_lzma = True
except ImportError:
    has_lzma = False


class ProxyModelWarning(Warning):
    pass

class CircularReferenceException(Exception):
    pass

def related_field_filter(lst):
    """ given a list of fields, return the ones that are related """

    ret = []
    for f in lst:
        s = str(f)
        if s.find('django.db.models.fields.related') >= 0:
            ret.append(f)

    return ret

def foreign_key_sort(items):
    """Perform topological sort.
       items is a list of django classes
       Returns a list of the items in one of the possible orders, or None
       if partial_order contains a loop.
    """

    def add_node(graph, node):
        """Add a node to the graph if not already exists."""
        if not node in graph:
            graph[node] = [0] # 0 = number of arcs coming into this node.

    def add_arc(graph, fromnode, tonode):
        """Add an arc to a graph. Can create multiple arcs.
           The end nodes must already exist."""
        graph[fromnode].append(tonode)
        # Update the count of incoming arcs in tonode.

        graph[tonode][0] = graph[tonode][0] + 1
    # step 1 - create a directed graph with an arc a->b for each input
    # pair (a,b).
    # The graph is represented by a dictionary. The dictionary contains
    # a pair item:list for each node in the graph. /item/ is the value
    # of the node. /list/'s 1st item is the count of incoming arcs, and
    # the rest are the destinations of the outgoing arcs. For example:
    #           {'a':[0,'b','c'], 'b':[1], 'c':[1]}
    # represents the graph:   c <-- a --> b
    # The graph may contain loops and multiple arcs.
    # Note that our representation does not contain reference loops to
    # cause GC problems even when the represented graph contains loops,
    # because we keep the node names rather than references to the nodes.
    graph = {}

    # iterate once for the nodes
    for v in items:
        add_node(graph, v)

    # iterate again to pull out the dependency information
    for a in items:

        rel_lst = related_field_filter(a._meta.fields)    # Add foreign keys
        rel_lst.extend( a._meta.many_to_many )            # Add many to many

        for b in rel_lst:
            # print "adding arc %s <- %s" % (b.rel.to, a)
            if b.related_model != a:
                add_arc(graph, b.related_model, a)


    # Step 2 - find all roots (nodes with zero incoming arcs).
    roots = [node for (node,nodeinfo) in graph.items() if nodeinfo[0] == 0]

    # step 3 - repeatedly emit a root and remove it from the graph. Removing
    # a node may convert some of the node's direct children into roots.
    # Whenever that happens, we append the new roots to the list of
    # current roots.
    sorted = []
    while len(roots) != 0:
        # If len(roots) is always 1 when we get here, it means that
        # the input describes a complete ordering and there is only
        # one possible output.
        # When len(roots) > 1, we can choose any root to send to the
        # output; this freedom represents the multiple complete orderings
        # that satisfy the input restrictions. We arbitrarily take one of
        # the roots using pop(). Note that for the algorithm to be efficient,
        # this operation must be done in O(1) time.

        root = roots.pop()
        sorted.append(root)
        for child in graph[root][1:]:
            graph[child][0] = graph[child][0] - 1
            if graph[child][0] == 0:
                roots.append(child)
        del graph[root]

    if len(graph.items()) != 0:
        # There is a loop in the input.
        pprint(graph)
        raise CircularReferenceException("Circular Dependency Detected in Input. %s" % graph.items())

    return sorted

class Command(BaseCommand):
    help = (
        "Output the contents of the database as a fixture of the given format "
        "(using each model's default manager unless --all is specified)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "args",
            metavar="app_label[.ModelName]",
            nargs="*",
            help=(
                "Restricts dumped data to the specified app_label or "
                "app_label.ModelName."
            ),
        )
        parser.add_argument(
            "--format",
            default="json",
            help="Specifies the output serialization format for fixtures.",
        )
        parser.add_argument(
            "--indent",
            type=int,
            help="Specifies the indent level to use when pretty-printing output.",
        )
        parser.add_argument(
            "--database",
            default=DEFAULT_DB_ALIAS,
            choices=tuple(connections),
            help="Nominates a specific database to dump fixtures from. "
            'Defaults to the "default" database.',
        )
        parser.add_argument(
            "-e",
            "--exclude",
            action="append",
            default=[],
            help="An app_label or app_label.ModelName to exclude "
            "(use multiple --exclude to exclude multiple apps/models).",
        )
        parser.add_argument(
            "--natural-foreign",
            action="store_true",
            dest="use_natural_foreign_keys",
            help="Use natural foreign keys if they are available.",
        )
        parser.add_argument(
            "--natural-primary",
            action="store_true",
            dest="use_natural_primary_keys",
            help="Use natural primary keys if they are available.",
        )
        parser.add_argument(
            "-a",
            "--all",
            action="store_true",
            dest="use_base_manager",
            help=(
                "Use Django's base manager to dump all models stored in the database, "
                "including those that would otherwise be filtered or modified by a "
                "custom manager."
            ),
        )
        parser.add_argument(
            "--pks",
            dest="primary_keys",
            help="Only dump objects with given primary keys. Accepts a comma-separated "
            "list of keys. This option only works when you specify one model.",
        )
        parser.add_argument(
            "-o", "--output", help="Specifies file to which the output is written."
        )

    def handle(self, *app_labels, **options):
        format = options["format"]
        indent = options["indent"]
        using = options["database"]
        excludes = options["exclude"]
        output = options["output"]
        show_traceback = options["traceback"]
        use_natural_foreign_keys = options["use_natural_foreign_keys"]
        use_natural_primary_keys = options["use_natural_primary_keys"]
        use_base_manager = options["use_base_manager"]
        pks = options["primary_keys"]

        if pks:
            primary_keys = [pk.strip() for pk in pks.split(",")]
        else:
            primary_keys = []

        excluded_models, excluded_apps = parse_apps_and_model_labels(excludes)

        if not app_labels:
            if primary_keys:
                raise CommandError("You can only use --pks option with one model")
            app_list = dict.fromkeys(
                app_config
                for app_config in apps.get_app_configs()
                if app_config.models_module is not None
                and app_config not in excluded_apps
            )
        else:
            if len(app_labels) > 1 and primary_keys:
                raise CommandError("You can only use --pks option with one model")
            app_list = {}
            for label in app_labels:
                try:
                    app_label, model_label = label.split(".")
                    try:
                        app_config = apps.get_app_config(app_label)
                    except LookupError as e:
                        raise CommandError(str(e))
                    if app_config.models_module is None or app_config in excluded_apps:
                        continue
                    try:
                        model = app_config.get_model(model_label)
                    except LookupError:
                        raise CommandError(
                            "Unknown model: %s.%s" % (app_label, model_label)
                        )

                    app_list_value = app_list.setdefault(app_config, [])

                    # We may have previously seen an "all-models" request for
                    # this app (no model qualifier was given). In this case
                    # there is no need adding specific models to the list.
                    if app_list_value is not None and model not in app_list_value:
                        app_list_value.append(model)
                except ValueError:
                    if primary_keys:
                        raise CommandError(
                            "You can only use --pks option with one model"
                        )
                    # This is just an app - no model qualifier
                    app_label = label
                    try:
                        app_config = apps.get_app_config(app_label)
                    except LookupError as e:
                        raise CommandError(str(e))
                    if app_config.models_module is None or app_config in excluded_apps:
                        continue
                    app_list[app_config] = None

        # Check that the serialization format exists; this is a shortcut to
        # avoid collating all the objects and _then_ failing.
        if format not in serializers.get_public_serializer_formats():
            try:
                serializers.get_serializer(format)
            except serializers.SerializerDoesNotExist:
                pass

            raise CommandError("Unknown serialization format: %s" % format)

        def get_objects(count_only=False):
            """
            Collate the objects to be serialized. If count_only is True, just
            count the number of objects to be serialized.
            """
            if use_natural_foreign_keys:
                models = serializers.sort_dependencies(
                    app_list.items(), allow_cycles=True
                )
            else:
                # There is no need to sort dependencies when natural foreign
                # keys are not used.
                models = []
                for app_config, model_list in app_list.items():
                    if model_list is None:
                        models.extend(app_config.get_models())
                    else:
                        models.extend(model_list)

            models = foreign_key_sort(models)

            for model in models:
                if model in excluded_models:
                    continue
                if model._meta.proxy and model._meta.proxy_for_model not in models:
                    warnings.warn(
                        "%s is a proxy model and won't be serialized."
                        % model._meta.label,
                        category=ProxyModelWarning,
                    )
                if not model._meta.proxy and router.allow_migrate_model(using, model):
                    if use_base_manager:
                        objects = model._base_manager
                    else:
                        objects = model._default_manager

                    queryset = objects.using(using).order_by(model._meta.pk.name)
                    if primary_keys:
                        queryset = queryset.filter(pk__in=primary_keys)
                    if count_only:
                        yield queryset.order_by().count()
                    else:
                        chunk_size = (
                            2000 if queryset._prefetch_related_lookups else None
                        )
                        yield from queryset.iterator(chunk_size=chunk_size)

        try:
            self.stdout.ending = None
            progress_output = None
            object_count = 0
            # If dumpdata is outputting to stdout, there is no way to display progress
            if output and self.stdout.isatty() and options["verbosity"] > 0:
                progress_output = self.stdout
                object_count = sum(get_objects(count_only=True))
            if output:
                file_root, file_ext = os.path.splitext(output)
                compression_formats = {
                    ".bz2": (open, {}, file_root),
                    ".gz": (gzip.open, {}, output),
                    ".lzma": (open, {}, file_root),
                    ".xz": (open, {}, file_root),
                    ".zip": (open, {}, file_root),
                }
                if has_bz2:
                    compression_formats[".bz2"] = (bz2.open, {}, output)
                if has_lzma:
                    compression_formats[".lzma"] = (
                        lzma.open,
                        {"format": lzma.FORMAT_ALONE},
                        output,
                    )
                    compression_formats[".xz"] = (lzma.open, {}, output)
                try:
                    open_method, kwargs, file_path = compression_formats[file_ext]
                except KeyError:
                    open_method, kwargs, file_path = (open, {}, output)
                if file_path != output:
                    file_name = os.path.basename(file_path)
                    warnings.warn(
                        f"Unsupported file extension ({file_ext}). "
                        f"Fixtures saved in '{file_name}'.",
                        RuntimeWarning,
                    )
                stream = open_method(file_path, "wt", **kwargs)
            else:
                stream = None
            try:
                serializers.serialize(
                    format,
                    get_objects(),
                    indent=indent,
                    use_natural_foreign_keys=use_natural_foreign_keys,
                    use_natural_primary_keys=use_natural_primary_keys,
                    stream=stream or self.stdout,
                    progress_output=progress_output,
                    object_count=object_count,
                )
            finally:
                if stream:
                    stream.close()
        except Exception as e:
            if show_traceback:
                raise
            raise CommandError("Unable to serialize database: %s" % e)
