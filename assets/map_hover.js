// Hover highlight for the circuits map. It only restyles the existing SVG shape of the country in the
// browser, so hovering never asks the server for anything and never makes plotly redraw the map.
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

    window.dash_clientside = Object.assign({}, window.dash_clientside, {
        map: {
            hover: function (hoverData) {
                const p = hoverData && hoverData.points && hoverData.points[0];
                highlightCountry(p && p.location ? p.location : null);
                return window.dash_clientside.no_update;
            }
        }
    });
})();
