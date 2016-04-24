(function(selector) {
    var charts = d3.selectAll(selector)[0];

    if (typeof charts === 'undefined')
        return;

    charts.forEach(function(chart) {
        var chart = d3.select(chart);
        var elem = chart[0][0];

        var width = chart.attr("data-width");
        if (width == null)
            width = getComputedStyle(elem.parentElement).width;
        width = parseInt(width);

        var data_url = chart.attr("data-report");
        if (data_url == null)
            return;

        var page_url = chart.attr("data-link");

        var title = chart.attr("title");

        var height = width * 1.2;

        var radius = Math.min(width, height) / 2;

        var color = d3.scale.ordinal()
            .range(["#7ED321", "#FFFFFF"]);

        var arc = d3.svg.arc()
            .outerRadius(radius)
            .innerRadius(radius - 40);

        var pie = d3.layout.pie()
            .value(function (d) {
                return d.value;
            })
            .sort(null);

        chart = chart
            .append('svg')
            .attr("width", width)
            .attr("height", height)
            .append("g")
            .attr("transform", "translate(" + (width / 2) + "," + (height / 2) + ")");

        if (page_url != null) {
            chart.on("click", function(d,i) {
                location.href = page_url;
            });
        }

        d3.json(data_url, function (error, data) {
            // calculate % client-side
            var uses = Math.round((data.uses / data.eligible) * 100);

            // just abort and leave it blank if something's wrong
            // (instead of showing "NaN%" visually)
            if (isNaN(uses))
                return;

            var pie_data = [
                {status: 'active', value: uses},
                {status: 'inactive', value: (100-uses)},
            ]

            var g = chart.selectAll(".arc")
                .data(pie(pie_data))
                .enter().append("g")
                .attr("class", "arc");

            g.append("path").style("fill", function(d) {
                return color(d.data.status);
            }).transition().delay(function(d, i) {
                return i *400;
            }).duration(400)
                .attrTween('d', function(d) {
                var i = d3.interpolate(d.startAngle+ 0.1, d.endAngle);
                return function(t) {
                    d.endAngle = i(t);
                    return arc(d);
                }
            });

            g.append("text")
                .attr("text-anchor", "middle")
                .attr("class", "total-value")
                .attr("dy", "0.2em")
                .attr("fill", "white")
                .text(function(d){
                    return "" + pie_data[0].value + "%";
            });

            g.append("text")
                .attr("text-anchor", "middle")
                .attr("class", "total-desc")
                .attr("dy", "2.5em")
                .attr("fill", "white")
                .text(function(d) {
                    return title;
            });

            chart.select("g").append("text")
                .attr("text-anchor", "middle")
                .attr("class", "total-detail")
                .attr("dy", (height / 2 / 5) * 2)
                .attr("fill", "white")
                .text(function(d) {
                    var f = function(n) { return d3.format(",")(n).replace(/,/g, '.'); }
                    return "" + f(data.uses) + " / " + f(data.eligible);
            });
        });
    });
})(".https_chart");