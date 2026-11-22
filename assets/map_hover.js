// Highlights the country under the mouse on the circuits map.
// Runs in the browser (clientside callback), so hovering never waits for the server.
window.dash_clientside = Object.assign({}, window.dash_clientside, {
    map: {
        hover: function (hoverData) {
            const noUpdate = window.dash_clientside.no_update;
            const gd = document.querySelector("#map .js-plotly-plot");
            if (!gd || !gd.data || !window.Plotly) return noUpdate;
            const idx = gd.data.findIndex(t => t.name === "hover-country");
            if (idx < 0) return noUpdate;

            let loc = null;
            if (hoverData && hoverData.points && hoverData.points.length) {
                loc = hoverData.points[0].location || null;
            }
            const current = (gd.data[idx].locations || [])[0] || null;
            if (current === loc) return noUpdate;
            window.Plotly.restyle(gd, {locations: [loc ? [loc] : []], z: [loc ? [1] : []]}, [idx]);
            return noUpdate;
        }
    }
});
