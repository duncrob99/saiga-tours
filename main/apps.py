from django.apps import AppConfig


class MainConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'main'

    def ready(self):
        import main.signals
        
        # Override silk's implementation of execute_sql to allow for binary data
        from django.core.exceptions import EmptyResultSet
        from django.utils import timezone
        import traceback
        from silk.collector import DataCollector
        from silk.sql import _should_wrap, _explain_query
        from django.utils.encoding import force_str
        import silk.sql

        def safe_force_str(param):
            if isinstance(param, bytes):
                return '<binary>'
            try:
                return force_str(param)
            except Exception:
                return '<unrenderable>'


        def patched_execute_sql(self, *args, **kwargs):
            try:
                q, params = self.as_sql()
                if not q:
                    raise EmptyResultSet
            except EmptyResultSet:
                result_type = args[0] if args else kwargs.get('result_type', 'multi')
                return iter([]) if result_type == 'multi' else None

            try:
                safe_params = tuple(safe_force_str(p) for p in params)
                sql_query = q % safe_params
            except Exception:
                sql_query = q  # fallback if param substitution fails

            if _should_wrap(sql_query):
                tb = ''.join(reversed(traceback.format_stack()))
                query_dict = {
                    'query': sql_query,
                    'start_time': timezone.now(),
                    'traceback': tb
                }
                try:
                    return self._execute_sql(*args, **kwargs)
                finally:
                    query_dict['end_time'] = timezone.now()
                    request = DataCollector().request
                    if request:
                        query_dict['request'] = request
                    if getattr(self.query.model, '__module__', '') != 'silk.models':
                        query_dict['analysis'] = _explain_query(self.connection, q, params)
                        DataCollector().register_query(query_dict)
                    else:
                        DataCollector().register_silk_query(query_dict)
            return self._execute_sql(*args, **kwargs)

        silk.sql.execute_sql = patched_execute_sql
