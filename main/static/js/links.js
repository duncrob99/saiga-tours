/*
window.link_table = new gridjs.Grid({
    columns: ['Model', 'Field', 'Text', 'URL', 'Domain', 'Empty', 'Relative', 'Resolves', 'Internal'],
    //server: {
        //url: '/list_links',
        //then: data => {
            //return data.links.map(link => [
                //gridjs.html(`<a href="${link.model_link}">${link.model}</a>`),
                //link.field,
                //link.text,
                //gridjs.html(`<a href="${link.url}">${link.url}</a>`),
                //link.domain,
                //link.empty ? 'Yes' : 'No',
                //link.relative ? 'Yes' : 'No',
                //link.resolves ? 'Yes' : 'No',
                //link.internal ? 'Yes' : 'No',
            //]);
        //}
    //},
    data: [
        ['Model', 'Field', 'Text', 'URL', 'Empty', 'Relative'],
    ],
    sort: true,
    search: true,
    resizable: true,
    fixedHeader: true,
    height: '100%',
    pagination: {
        enabled: true,
        limit: 50,
    },
}).render(document.getElementById("table-wrapper"));
*/

(async function() {
    function display_bool(value) {
        return value ? 'Yes' : 'No';
    }

    const table = document.querySelector('#table');
    const table_body = table.querySelector('tbody');

    const response = await fetch('/list_links');

    if (response.ok) {
        const links = (await response.json()).links;
        console.log(links);

        for (let link of links) {
            let row = document.createElement('tr');

            row.innerHTML = `
                <td><a href="${link.model_link}">${link.model}</a></td>
                <td>${link.field}</td>
                <td>${link.text}</td>
                <td><a href="${link.url}">${link.url}</a></td>
                <td>${link.domain}</td>
                <td>${display_bool(link.empty)}</td>
                <td>${display_bool(link.relative)}</td>
                <td>${display_bool(link.resolves)}</td>
                <td>${display_bool(link.internal)}</td>
                <td>${display_bool(link.is_broken)}</td>
            `;

            table_body.appendChild(row);
        }
    }

    table.classList.remove('loading');

    const getCellValue = (tr, idx) => tr.children[idx].innerText || tr.children[idx].textContent;

    const comparer = (idx, asc) => (a, b) => ((v1, v2) => 
        v1 !== '' && v2 !== '' && !isNaN(v1) && !isNaN(v2) ? v1 - v2 : v1.toString().localeCompare(v2)
        )(getCellValue(asc ? a : b, idx), getCellValue(asc ? b : a, idx));

    // do the work...
    document.querySelectorAll('th').forEach(th => th.addEventListener('click', (() => {
        const table = th.closest('table');
        const tbody = table.querySelector('tbody');
        Array.from(tbody.querySelectorAll('tr'))
            .sort(comparer(Array.from(th.parentNode.children).indexOf(th), this.asc = !this.asc))
            .forEach(tr => tbody.appendChild(tr));
        document.querySelectorAll('th').forEach(th => th.classList.remove('asc', 'desc'));
        if (this.asc) {
            th.classList.remove('asc');
            th.classList.add('desc');
        } else {
            th.classList.remove('desc');
            th.classList.add('asc');
        }
        })
    ));
})();
