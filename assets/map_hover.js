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

    // ---------------------------------------------------------------- driver / team pages: race list <-> map
    // rows of the race lists carry data-map (id of their page's map), data-lon/lat, data-label, data-circuit
    let point = null;     // {copy, label}

    function clearPoint() {
        if (point) {
            point.copy.remove();
            if (point.label) point.label.classList.remove("show");
            point = null;
        }
    }

    function highlightPoint(mapId, lon, lat, text) {
        clearPoint();
        const gd = document.querySelector("#" + mapId + " .js-plotly-plot");
        if (!gd) return;
        const el = Array.from(gd.querySelectorAll(".scattergeo path.point")).find(p => {
            const ll = p.__data__ && p.__data__.lonlat;
            return ll && Math.abs(ll[0] - lon) < 1e-6 && Math.abs(ll[1] - lat) < 1e-6;
        });
        if (!el) return;
        // draw an enlarged copy above every trace: restyling the marker itself left it under the markers of
        // later traces (e.g. a red "raced here" circuit next to a gold one)
        const label = document.getElementById(mapId + "-label");
        const copy = el.cloneNode(false);
        copy.setAttribute("transform", (el.getAttribute("transform") || "") + " scale(1.8)");
        copy.style.stroke = "#ffffff";
        copy.style.strokeWidth = "2.5px";
        copy.style.opacity = "1";
        copy.style.pointerEvents = "none";
        (el.closest(".frontplot") || el.parentNode).appendChild(copy);
        point = {copy, label};
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
        highlightPoint(row.dataset.map || "driver-map", parseFloat(row.dataset.lon), parseFloat(row.dataset.lat),
                       row.dataset.label);
    });
    document.addEventListener("mouseout", function (e) {
        const row = e.target.closest && e.target.closest(".dr-race");
        if (row && !row.contains(e.relatedTarget)) {
            lastRow = null;
            clearPoint();
        }
    });

    // rows of the team's race list have no dash ids (there can be 1000+), so their clicks go through a store
    document.addEventListener("click", function (e) {
        const row = e.target.closest && e.target.closest(".dr-race[data-race]");
        if (row && window.dash_clientside && window.dash_clientside.set_props) {
            window.dash_clientside.set_props("race-click", {data: {race: parseInt(row.dataset.race, 10), t: Date.now()}});
        }
    });

    function highlightRows(listId, circuit) {
        const list = document.getElementById(listId);
        if (!list) return;
        list.querySelectorAll(".dr-race.hl").forEach(r => r.classList.remove("hl"));
        if (circuit) {
            list.querySelectorAll('.dr-race[data-circuit="' + circuit + '"]').forEach(r => r.classList.add("hl"));
        }
    }

    function circuitOf(hoverData) {
        const p = hoverData && hoverData.points && hoverData.points[0];
        return p && p.customdata ? p.customdata[0] : null;
    }

    // ---------------------------------------------------------------- team page: race list
    // built here as one html string: 1000+ rows as dash components took tens of seconds to render
    const esc = s => String(s == null ? "" : s).replace(/[&<>"']/g,
        c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));

    function renderTeamRaces(rows) {
        const el = document.getElementById("team-races");
        if (!el) return;
        if (!rows || !rows.length) {
            el.innerHTML = rows ? '<p class="note">No races</p>' : "";
            return;
        }
        const body = rows.map(r => {
            const cars = r.cars.map(c => esc(c[0]) + ' <span class="' + esc(c[2]) + '" title="' + esc(c[3]) + '">'
                + esc(c[1]) + "</span>").join(" &nbsp; ");
            return '<tr class="dr-race" title="Click to open this race" data-map="team-map"'
                + ' data-race="' + r.race + '" data-circuit="' + esc(r.circuit) + '" data-lon="' + esc(r.lon)
                + '" data-lat="' + esc(r.lat) + '" data-label="' + esc(r.label) + '">'
                + '<td class="pos">' + r.year + "</td>"
                + '<td class="bar" style="background:' + esc(r.colour) + '"></td>'
                + "<td><div>" + esc(r.gp) + '</div><div class="team">' + cars + "</div></td>"
                + "<td>" + esc(r.points) + "</td></tr>";
        }).join("");
        el.innerHTML = '<table class="classification"><tbody>' + body + "</tbody></table>";
        el.scrollTop = 0;
    }

    window.dash_clientside = Object.assign({}, window.dash_clientside, {
        map: {
            renderTeamRaces: function (rows) {
                renderTeamRaces(rows);
                return window.dash_clientside.no_update;
            },
            hover: function (hoverData) {
                const p = hoverData && hoverData.points && hoverData.points[0];
                highlightCountry(p && p.location ? p.location : null);
                return window.dash_clientside.no_update;
            },
            driverHover: function (hoverData) {
                highlightRows("driver-races", circuitOf(hoverData));
                return window.dash_clientside.no_update;
            },
            teamHover: function (hoverData) {
                highlightRows("team-races", circuitOf(hoverData));
                return window.dash_clientside.no_update;
            }
        }
    });
})();
