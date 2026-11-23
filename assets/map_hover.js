// Hover highlights for the maps. Everything here only restyles existing SVG shapes in the browser,
// so hovering never asks the server for anything and never makes plotly redraw the map.
(function () {
    // ---------------------------------------------------------------- circuits map: hovered country
    let country = null;   // {el, loc, style}

    function clearCountry() {
        if (country) {
            country.el.setAttribute("style", country.style);
            country = null;
        }
    }

    function highlightCountry(loc) {
        if (country && country.loc === loc && country.el.isConnected) return;
        clearCountry();
        if (!loc) return;
        const gd = document.querySelector("#map .js-plotly-plot");
        // the first choropleth trace is the layer of all countries
        const layer = gd && gd.querySelector(".trace.choropleth");
        if (!layer) return;
        const el = Array.from(layer.querySelectorAll("path.choroplethlocation"))
            .find(p => p.__data__ && p.__data__.loc === loc);
        if (!el) return;
        country = {el, loc, style: el.getAttribute("style") || ""};
        el.style.fill = "#55557a";
        el.style.stroke = "#ffffff";
        el.style.strokeWidth = "1.2px";
        el.style.strokeOpacity = "1";
        el.parentNode.appendChild(el);   // on top of its neighbours, so the whole outline shows
    }

    // ---------------------------------------------------------------- driver page: race list <-> map
    let point = null;     // {el, transform, style}

    function clearPoint() {
        if (point) {
            point.el.setAttribute("transform", point.transform);
            point.el.setAttribute("style", point.style);
            point = null;
        }
        const label = document.getElementById("driver-map-label");
        if (label) label.classList.remove("show");
    }

    function highlightPoint(lon, lat, text) {
        clearPoint();
        const gd = document.querySelector("#driver-map .js-plotly-plot");
        if (!gd) return;
        const el = Array.from(gd.querySelectorAll(".scattergeo path.point")).find(p => {
            const ll = p.__data__ && p.__data__.lonlat;
            return ll && Math.abs(ll[0] - lon) < 1e-6 && Math.abs(ll[1] - lat) < 1e-6;
        });
        if (!el) return;
        point = {el, transform: el.getAttribute("transform") || "", style: el.getAttribute("style") || ""};
        el.setAttribute("transform", point.transform + " scale(1.8)");
        el.style.stroke = "#ffffff";
        el.style.strokeWidth = "2.5px";
        el.style.opacity = "1";
        el.parentNode.appendChild(el);
        const label = document.getElementById("driver-map-label");
        if (label && text) {
            label.textContent = text;
            label.classList.add("show");
        }
    }

    let lastRow = null;
    document.addEventListener("mouseover", function (e) {
        const row = e.target.closest && e.target.closest(".dr-race");
        if (!row || row === lastRow) return;
        lastRow = row;
        highlightPoint(parseFloat(row.dataset.lon), parseFloat(row.dataset.lat), row.dataset.label);
    });
    document.addEventListener("mouseout", function (e) {
        const row = e.target.closest && e.target.closest(".dr-race");
        if (row && !row.contains(e.relatedTarget)) {
            lastRow = null;
            clearPoint();
        }
    });

    function highlightRows(circuit) {
        document.querySelectorAll(".dr-race.hl").forEach(r => r.classList.remove("hl"));
        if (circuit) {
            document.querySelectorAll('.dr-race[data-circuit="' + circuit + '"]')
                .forEach(r => r.classList.add("hl"));
        }
    }

    window.dash_clientside = Object.assign({}, window.dash_clientside, {
        map: {
            hover: function (hoverData) {
                const p = hoverData && hoverData.points && hoverData.points[0];
                highlightCountry(p && p.location ? p.location : null);
                return window.dash_clientside.no_update;
            },
            driverHover: function (hoverData) {
                const p = hoverData && hoverData.points && hoverData.points[0];
                highlightRows(p && p.customdata ? p.customdata[0] : null);
                return window.dash_clientside.no_update;
            }
        }
    });
})();
