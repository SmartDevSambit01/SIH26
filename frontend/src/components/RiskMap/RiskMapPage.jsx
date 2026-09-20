import React, { useState, useEffect, useRef } from "react";
import * as maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import {
  Search,
  ArrowLeft,
  AlertTriangle,
  MapPin,
  Bell,
  ChevronDown,
} from "lucide-react";
import DistrictSelector from "./DistrictSelector";
import MapLegend from "./MapLegend";
import CellDetailsModal from "./CellDetailsModal";
import SystemStatusPill from "./SystemStatusPill";
import AlertPanel from "./AlertPanel";
import AreaSearchPanel from "./AreaSearchPanel";
import AreaRiskDashboard from "./AreaRiskDashboard";
import "./RiskMap.css";

const DISTRICT_CONFIG = {
  Kohima: {
    name: "Kohima",
    state: "Nagaland",
    center: [94.096, 25.773],
    zoom: 10.2,
    cells: 6055,
    gridFile: "/data/kohima_grid.geojson",
    boundaryFile: "/data/kohima_boundary.geojson",
  },
  Aizawl: {
    name: "Aizawl",
    state: "Mizoram",
    center: [92.825, 23.864],
    zoom: 9.8,
    cells: 10906,
    gridFile: "/data/aizawl_grid.geojson",
    boundaryFile: "/data/aizawl_boundary.geojson",
  },
};

const BASEMAP_STYLES = {
  satellite: {
    version: 8,
    sources: {
      "esri-satellite": {
        type: "raster",
        tiles: [
          "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        ],
        tileSize: 256,
        attribution: "Esri, Maxar, Earthstar Geographics",
      },
    },
    layers: [
      {
        id: "esri-satellite-layer",
        type: "raster",
        source: "esri-satellite",
        minzoom: 0,
        maxzoom: 19,
      },
    ],
  },
  dark: {
    version: 8,
    sources: {
      "carto-dark": {
        type: "raster",
        tiles: [
          "https://basemaps.cartocdn.com/rastertiles/dark_all/{z}/{x}/{y}.png",
        ],
        tileSize: 256,
        attribution: "© CartoDB, © OpenStreetMap contributors",
      },
    },
    layers: [
      {
        id: "carto-dark-layer",
        type: "raster",
        source: "carto-dark",
        minzoom: 0,
        maxzoom: 19,
      },
    ],
  },
};

export default function RiskMapPage({
  initialDistrict = "Kohima",
  initialShowAlerts = false,
  onNavigate,
}) {
  const [district, setDistrict] = useState(initialDistrict);
  const [selectedCell, setSelectedCell] = useState(null);
  const [hoveredCell, setHoveredCell] = useState(null);
  const [hoverPosition, setHoverPosition] = useState(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [showGrid, setShowGrid] = useState(true);
  const [showBoundary, setShowBoundary] = useState(true);
  const [showHistorical, setShowHistorical] = useState(true);
  const [showFlood, setShowFlood] = useState(false);
  const [basemapType, setBasemapType] = useState("satellite");
  const [isLoadingData, setIsLoadingData] = useState(false);
  const [showAlertPanel, setShowAlertPanel] = useState(initialShowAlerts);

  // Real dynamic-feed freshness status (GPM/SMAP/Sentinel-1), fetched from the
  // backend rather than hardcoded — feeds SystemStatusPill and MapLegend.
  const [dataStatus, setDataStatus] = useState(null);
  const [backendReachable, setBackendReachable] = useState(true);

  // Area Locality Intelligence States (TASK 11)
  const [showAreaSearch, setShowAreaSearch] = useState(false);
  const [selectedAreaId, setSelectedAreaId] = useState(null);
  const [associatedAreaCells, setAssociatedAreaCells] = useState([]);
  const [showDistrictMenu, setShowDistrictMenu] = useState(false);
  const districtDropdownRef = useRef(null);
  const searchDropdownRef = useRef(null);
  const popupRef = useRef(null);

  const mapContainerRef = useRef(null);
  const mapRef = useRef(null);
  const gridDataRef = useRef(null);
  const prevBasemapRef = useRef(basemapType);
  const currentRequestRef = useRef(0);
  // Keep a ref so event-handler closures always see the current district
  const districtRef = useRef(initialDistrict);

  // Helper: Safely teardown all layers using a source, then remove the source
  const safeRemoveSourceAndLayers = (sourceId) => {
    const map = mapRef.current;
    if (!map) return;
    try {
      const style = map.getStyle();
      if (style && style.layers) {
        style.layers.forEach((layer) => {
          if (layer.source === sourceId) {
            if (map.getLayer(layer.id)) {
              map.removeLayer(layer.id);
            }
          }
        });
      }
      if (map.getSource(sourceId)) {
        map.removeSource(sourceId);
      }
    } catch (e) {
      console.warn(`Cleanup source ${sourceId} warning:`, e);
    }
  };

  // Helper: Switch active district, move camera, and load district GIS layers
  const switchDistrict = (targetDistrict) => {
    districtRef.current = targetDistrict;
    setDistrict(targetDistrict);
    setSelectedCell(null);
    if (popupRef.current) {
      popupRef.current.remove();
      popupRef.current = null;
    }
    clearAreaHighlight();
    setSelectedAreaId(null);

    const map = mapRef.current;
    if (!map) return;

    const cfg = DISTRICT_CONFIG[targetDistrict];
    if (!cfg) return;

    map.flyTo({
      center: cfg.center,
      zoom: cfg.zoom,
      duration: 1600,
      essential: true,
    });

    // Load layers immediately — loadDistrictLayers guards style readiness internally
    loadDistrictLayers(targetDistrict);
  };

  // Initialize Map
  useEffect(() => {
    if (!mapContainerRef.current) return;

    const initialCfg =
      DISTRICT_CONFIG[districtRef.current] || DISTRICT_CONFIG.Kohima;

    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      style: BASEMAP_STYLES[basemapType],
      center: initialCfg.center,
      zoom: initialCfg.zoom,
      minZoom: 7,
      maxZoom: 18,
      attributionControl: false,
    });

    map.addControl(
      new maplibregl.NavigationControl({ showCompass: true }),
      "top-right",
    );
    map.addControl(
      new maplibregl.AttributionControl({ compact: true }),
      "bottom-right",
    );

    mapRef.current = map;

    const triggerInitialLoad = () => {
      loadDistrictLayers(districtRef.current);
      loadHistoricalLandslides();
    };

    if (map.isStyleLoaded()) {
      triggerInitialLoad();
    } else {
      map.once("load", triggerInitialLoad);
      map.once("style.load", triggerInitialLoad);
    }

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Update Basemap Style (only when basemapType actually changes)
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    if (prevBasemapRef.current === basemapType) return;
    prevBasemapRef.current = basemapType;

    map.setStyle(BASEMAP_STYLES[basemapType], { diff: false });
    map.once("style.load", () => {
      // Use ref so this closure always sees the current district
      loadDistrictLayers(districtRef.current);
      loadHistoricalLandslides();
    });
  }, [basemapType]);

  // Fetch real dynamic-feed freshness status (GPM/SMAP/Sentinel-1) for the
  // current district. Replaces hardcoded status text in SystemStatusPill/MapLegend.
  useEffect(() => {
    let cancelled = false;
    const hosts = [
      import.meta.env.VITE_API_URL || "",
      "http://127.0.0.1:8000",
      "http://localhost:8000",
    ];

    (async () => {
      for (const host of hosts) {
        try {
          const [rainRes, smRes, satRes] = await Promise.all([
            fetch(`${host}/api/rainfall/latest?district=${district}&limit=1`),
            fetch(
              `${host}/api/soil-moisture/latest?district=${district}&limit=1`,
            ),
            fetch(`${host}/api/satellite/latest?district=${district}&limit=1`),
          ]);
          if (rainRes.ok && smRes.ok && satRes.ok) {
            const [rain, sm, sat] = await Promise.all([
              rainRes.json(),
              smRes.json(),
              satRes.json(),
            ]);
            if (!cancelled) {
              setDataStatus({
                rainfall: {
                  status: rain.data_status,
                  timestamp:
                    rain.observations?.[0]?.observation_timestamp || null,
                },
                soil_moisture: {
                  status: sm.data_status,
                  timestamp:
                    sm.observations?.[0]?.observation_timestamp || null,
                },
                satellite: {
                  status: sat.data_status,
                  timestamp:
                    sat.observations?.[0]?.observation_timestamp || null,
                },
              });
              setBackendReachable(true);
            }
            return;
          }
        } catch (err) {
          // try next host
        }
      }
      if (!cancelled) setBackendReachable(false);
    })();

    return () => {
      cancelled = true;
    };
  }, [district]);

  // Close the district/search dropdowns when clicking outside them
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (
        districtDropdownRef.current &&
        !districtDropdownRef.current.contains(e.target)
      ) {
        setShowDistrictMenu(false);
      }
      if (
        searchDropdownRef.current &&
        !searchDropdownRef.current.contains(e.target)
      ) {
        setShowAreaSearch(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Highlight area cells on map when selectedAreaId changes
  useEffect(() => {
    if (!selectedAreaId) {
      clearAreaHighlight();
      return;
    }
    fetchAndHighlightArea(selectedAreaId);
  }, [selectedAreaId]);

  const clearAreaHighlight = () => {
    safeRemoveSourceAndLayers("area-highlight-source");
    setAssociatedAreaCells([]);
  };

  const fetchAndHighlightArea = async (areaId) => {
    const map = mapRef.current;
    if (!map) return;

    const hosts = [
      import.meta.env.VITE_API_URL || "",
      "http://127.0.0.1:8000",
      "http://localhost:8000",
    ];

    let data = null;
    for (const host of hosts) {
      try {
        const res = await fetch(`${host}/api/areas/${areaId}/cells`);
        if (res.ok) {
          data = await res.json();
          break;
        }
      } catch (e) {}
    }

    if (!data) return;

    // Seamless Cross-District Switch: if area belongs to a different district, load its layers first
    if (data.district && data.district !== district) {
      await loadDistrictLayers(data.district);
      setDistrict(data.district);
      const cfg = DISTRICT_CONFIG[data.district];
      if (cfg && map) {
        map.flyTo({ center: cfg.center, zoom: cfg.zoom, duration: 1400 });
      }
    }

    if (!gridDataRef.current || !gridDataRef.current.features) return;

    const cellIds = new Set(data.cells.map((c) => c.cell_id));
    setAssociatedAreaCells(data.cells);

    // Filter grid GeoJSON features
    const matchingFeatures = gridDataRef.current.features.filter((f) =>
      cellIds.has(f.properties.cell_id),
    );

    if (matchingFeatures.length > 0) {
      // Calculate Bounding Box
      let minLat = 90,
        maxLat = -90,
        minLon = 180,
        maxLon = -180;
      matchingFeatures.forEach((f) => {
        const lat = f.properties.centroid_lat;
        const lon = f.properties.centroid_lon;
        if (lat < minLat) minLat = lat;
        if (lat > maxLat) maxLat = lat;
        if (lon < minLon) minLon = lon;
        if (lon > maxLon) maxLon = lon;
      });

      // Fit Map to Area Bounds
      map.fitBounds(
        [
          [minLon, minLat],
          [maxLon, maxLat],
        ],
        { padding: 80, maxZoom: 14.5, duration: 1600 },
      );

      // Highlight Layer on Map
      const areaGeojson = {
        type: "FeatureCollection",
        features: matchingFeatures,
      };

      clearAreaHighlight();

      map.addSource("area-highlight-source", {
        type: "geojson",
        data: areaGeojson,
      });

      map.addLayer({
        id: "area-highlight-fill",
        type: "fill",
        source: "area-highlight-source",
        paint: {
          "fill-color": "#38BDF8",
          "fill-opacity": 0.25,
        },
      });

      map.addLayer({
        id: "area-highlight-line",
        type: "line",
        source: "area-highlight-source",
        paint: {
          "line-color": "#38BDF8",
          "line-width": 2.8,
          "line-opacity": 0.95,
        },
      });
    }
  };

  // Load District Grid and Boundary
  const loadDistrictLayers = async (targetDistrict) => {
    const map = mapRef.current;
    if (!map) return;

    // Critical: do not attempt to add sources/layers until the style is fully loaded
    if (!map.isStyleLoaded()) {
      map.once("style.load", () => loadDistrictLayers(targetDistrict));
      return;
    }

    const cfg = DISTRICT_CONFIG[targetDistrict];
    if (!cfg) return;

    const requestId = ++currentRequestRef.current;
    setIsLoadingData(true);

    try {
      // 1. Fetch District Boundary
      const boundaryRes = await fetch(cfg.boundaryFile);
      const boundaryGeojson = await boundaryRes.json();

      // 2. Fetch 500m Enriched Grid
      const gridRes = await fetch(cfg.gridFile);
      const gridGeojson = await gridRes.json();

      // Out-of-order request protection
      if (requestId !== currentRequestRef.current) {
        return;
      }

      // Double-check that the style is still loaded after the async fetches
      // (large GeoJSON files can take seconds; style may have been reset in that time)
      if (!map.isStyleLoaded()) {
        console.warn(
          "Style was reset during GeoJSON fetch; aborting layer add",
        );
        return;
      }

      gridDataRef.current = gridGeojson;

      // Safely clear existing district boundary and risk grid sources/layers
      safeRemoveSourceAndLayers("district-boundary");
      safeRemoveSourceAndLayers("risk-grid");

      // Add Boundary Source & Layer
      map.addSource("district-boundary", {
        type: "geojson",
        data: boundaryGeojson,
      });

      map.addLayer({
        id: "district-boundary-line",
        type: "line",
        source: "district-boundary",
        paint: {
          "line-color": "#00E599",
          "line-width": 3.0,
          "line-opacity": 0.95,
        },
      });

      // Add Grid Source
      map.addSource("risk-grid", {
        type: "geojson",
        data: gridGeojson,
        promoteId: "cell_id",
      });

      // Grid Polygon Fill Layer (Risk Colors)
      map.addLayer({
        id: "risk-grid-fill",
        type: "fill",
        source: "risk-grid",
        layout: {
          visibility: showGrid ? "visible" : "none",
        },
        paint: {
          "fill-color": [
            "case",
            ["has", "risk_color"],
            ["get", "risk_color"],
            [
              "match",
              ["get", "risk_class"],
              "CRITICAL",
              "#A855F7",
              "HIGH",
              "#EF4444",
              "WARNING",
              "#F97316",
              "WATCH",
              "#EAB308",
              "LOW",
              "#22C55E",
              "VERY_LOW",
              "#10B981",
              "#4B5563",
            ],
          ],
          "fill-opacity": 0.65,
        },
      });

      // Grid Wireframe Stroke Layer
      map.addLayer({
        id: "risk-grid-line",
        type: "line",
        source: "risk-grid",
        layout: {
          visibility: showGrid ? "visible" : "none",
        },
        paint: {
          "line-color": "#FFFFFF",
          "line-width": 0.8,
          "line-opacity": 0.45,
        },
      });

      // Flash-Flood Susceptibility Fill Layer (static, DEM-derived; independent toggle)
      map.addLayer({
        id: "flood-grid-fill",
        type: "fill",
        source: "risk-grid",
        layout: {
          visibility: showFlood ? "visible" : "none",
        },
        paint: {
          "fill-color": [
            "case",
            ["==", ["get", "flood_status"], "AVAILABLE"],
            ["get", "ffsi_color"],
            "#4B5563",
          ],
          "fill-opacity": 0.65,
        },
      });

      // Selected Cell Highlight
      map.addLayer({
        id: "risk-grid-highlight",
        type: "line",
        source: "risk-grid",
        paint: {
          "line-color": "#FFFFFF",
          "line-width": 3.5,
          "line-opacity": [
            "case",
            ["boolean", ["feature-state", "selected"], false],
            1.0,
            0.0,
          ],
        },
      });

      // Interactive Events on Grid Cells
      map.off("mousemove", "risk-grid-fill", handleCellHover);
      map.off("mouseleave", "risk-grid-fill", handleCellMouseLeave);
      map.off("click", "risk-grid-fill", handleCellClick);

      map.on("mousemove", "risk-grid-fill", handleCellHover);
      map.on("mouseleave", "risk-grid-fill", handleCellMouseLeave);
      map.on("click", "risk-grid-fill", handleCellClick);
    } catch (err) {
      console.error("Failed to load district GIS layers:", err);
    } finally {
      if (requestId === currentRequestRef.current) {
        setIsLoadingData(false);
      }
    }
  };

  // Load Verified Historical Landslides
  const loadHistoricalLandslides = async () => {
    const map = mapRef.current;
    if (!map) return;

    try {
      const res = await fetch("/data/verified_landslides.geojson");
      const geojson = await res.json();

      safeRemoveSourceAndLayers("historical-events");

      map.addSource("historical-events", {
        type: "geojson",
        data: geojson,
      });

      // Outer Halo for High Visibility
      map.addLayer({
        id: "historical-events-halo",
        type: "circle",
        source: "historical-events",
        layout: {
          visibility: showHistorical ? "visible" : "none",
        },
        paint: {
          "circle-radius": 11,
          "circle-color": "#EF4444",
          "circle-opacity": 0.35,
          "circle-stroke-width": 1,
          "circle-stroke-color": "#FCA5A5",
        },
      });

      // Core Point
      map.addLayer({
        id: "historical-events-point",
        type: "circle",
        source: "historical-events",
        layout: {
          visibility: showHistorical ? "visible" : "none",
        },
        paint: {
          "circle-radius": 6,
          "circle-color": "#DC2626",
          "circle-stroke-width": 2,
          "circle-stroke-color": "#FFFFFF",
        },
      });

      const handleHistoricalClick = (e) => {
        if (!e.features || !e.features[0]) return;
        const props = e.features[0].properties;
        const cid = props.cell_id;
        if (cid) searchAndSelectCell(cid);
      };

      map.off("click", "historical-events-point", handleHistoricalClick);
      map.on("click", "historical-events-point", handleHistoricalClick);
    } catch (err) {
      console.error("Failed to load historical landslides:", err);
    }
  };

  // Hover Interaction
  const handleCellHover = (e) => {
    if (!e.features || !e.features[0]) return;
    const map = mapRef.current;
    if (map) map.getCanvas().style.cursor = "pointer";

    const feat = e.features[0];
    setHoveredCell(feat.properties);
    setHoverPosition({ x: e.point.x, y: e.point.y });
  };

  const handleCellMouseLeave = () => {
    const map = mapRef.current;
    if (map) map.getCanvas().style.cursor = "";
    setHoveredCell(null);
    setHoverPosition(null);
  };

  // Click Interaction
  const handleCellClick = (e) => {
    if (!e.features || !e.features[0]) return;
    const feat = e.features[0];
    const props = feat.properties;

    selectCellFeature(props);
    showCellPopup(props, e.lngLat);
  };

  // Small floating "Cell: KOH_01432 · Risk: High" bubble anchored to the clicked
  // cell's real coordinates — uses MapLibre's own Popup so it stays correctly
  // positioned through pan/zoom instead of tracking screen pixels by hand.
  const showCellPopup = (props, lngLat) => {
    const map = mapRef.current;
    if (!map) return;
    if (popupRef.current) popupRef.current.remove();

    const el = document.createElement("div");
    el.className = "sarvas-cell-popup-content";
    el.innerHTML = `
      <div class="sarvas-cell-popup-id">Cell: ${props.cell_id}</div>
      <div class="sarvas-cell-popup-risk" style="color:${props.risk_color || "#94A3B8"}">
        Risk: ${props.risk_badge || props.risk_class || "Unavailable"}
      </div>
    `;

    popupRef.current = new maplibregl.Popup({
      closeButton: true,
      closeOnClick: false,
      offset: 14,
      className: "sarvas-cell-popup",
    })
      .setLngLat(lngLat)
      .setDOMContent(el)
      .addTo(map);
  };

  const selectCellFeature = (props) => {
    const map = mapRef.current;
    if (!map) return;

    if (selectedCell) {
      map.setFeatureState(
        { source: "risk-grid", id: selectedCell.cell_id },
        { selected: false },
      );
    }

    map.setFeatureState(
      { source: "risk-grid", id: props.cell_id },
      { selected: true },
    );

    setSelectedCell(props);
  };

  // Search by Cell ID, Area Name, or Historical Event ID
  const handleSearchSubmit = async (e) => {
    e.preventDefault();
    if (!searchTerm.trim()) return;

    const term = searchTerm.trim();
    const termUpper = term.toUpperCase();

    // 1. Check if Cell ID or Historical Event ID
    if (
      termUpper.startsWith("KOH_") ||
      termUpper.startsWith("AIZ_") ||
      termUpper.startsWith("LS_")
    ) {
      searchAndSelectCell(termUpper);
      setShowAreaSearch(false);
      setSearchTerm("");
      return;
    }

    // 2. Check if District Name search (Kohima / Aizawl)
    if (termUpper === "KOHIMA") {
      switchDistrict("Kohima");
      setShowAreaSearch(false);
      setSearchTerm("");
      return;
    } else if (termUpper === "AIZAWL") {
      switchDistrict("Aizawl");
      setShowAreaSearch(false);
      setSearchTerm("");
      return;
    }

    // 3. Search Area / Locality Index via Backend API with Multi-Host Fallback
    const hosts = [
      import.meta.env.VITE_API_URL || "",
      "http://127.0.0.1:8000",
      "http://localhost:8000",
    ];

    for (const host of hosts) {
      try {
        const res = await fetch(
          `${host}/api/areas?search=${encodeURIComponent(term)}`,
        );
        if (res.ok) {
          const areas = await res.json();
          if (areas.length > 0) {
            setSelectedAreaId(areas[0].area_id);
            setShowAreaSearch(false);
            setSearchTerm("");
            return;
          }
        }
      } catch (err) {}
    }

    // Fallback to searching grid features
    searchAndSelectCell(termUpper);
  };

  const searchAndSelectCell = (term) => {
    const map = mapRef.current;
    if (!map || !gridDataRef.current) return;

    if (term.startsWith("AIZ_") && district !== "Aizawl") {
      setDistrict("Aizawl");
      setTimeout(() => searchAndSelectCell(term), 1200);
      return;
    } else if (term.startsWith("KOH_") && district !== "Kohima") {
      setDistrict("Kohima");
      setTimeout(() => searchAndSelectCell(term), 1200);
      return;
    }

    const feature = gridDataRef.current.features.find(
      (f) =>
        f.properties.cell_id.toUpperCase() === term ||
        (f.properties.event_id && f.properties.event_id.toUpperCase() === term),
    );

    if (feature) {
      const coords = [
        feature.properties.centroid_lon,
        feature.properties.centroid_lat,
      ];
      map.flyTo({
        center: coords,
        zoom: 13.5,
        duration: 1400,
        essential: true,
      });

      selectCellFeature(feature.properties);
    } else {
      alert(`Cell ID, area, or verified event "${term}" not found.`);
    }
  };

  // Toggle Visibility
  const handleToggleGrid = (visible) => {
    setShowGrid(visible);
    const map = mapRef.current;
    if (map && map.getLayer("risk-grid-fill")) {
      map.setLayoutProperty(
        "risk-grid-fill",
        "visibility",
        visible ? "visible" : "none",
      );
      map.setLayoutProperty(
        "risk-grid-line",
        "visibility",
        visible ? "visible" : "none",
      );
    }
    if (visible && map && map.getLayer("flood-grid-fill")) {
      map.setLayoutProperty("flood-grid-fill", "visibility", "none");
      setShowFlood(false);
    }
  };

  const handleToggleBoundary = (visible) => {
    setShowBoundary(visible);
    const map = mapRef.current;
    if (map && map.getLayer("district-boundary-line")) {
      map.setLayoutProperty(
        "district-boundary-line",
        "visibility",
        visible ? "visible" : "none",
      );
    }
  };

  const handleToggleHistorical = (visible) => {
    setShowHistorical(visible);
    const map = mapRef.current;
    if (map && map.getLayer("historical-events-point")) {
      map.setLayoutProperty(
        "historical-events-point",
        "visibility",
        visible ? "visible" : "none",
      );
      map.setLayoutProperty(
        "historical-events-halo",
        "visibility",
        visible ? "visible" : "none",
      );
    }
  };

  const handleToggleFlood = (visible) => {
    setShowFlood(visible);
    const map = mapRef.current;
    if (map && map.getLayer("flood-grid-fill")) {
      map.setLayoutProperty(
        "flood-grid-fill",
        "visibility",
        visible ? "visible" : "none",
      );
    }
    // Flood and landslide-risk fills occupy the same map space; showing both at
    // once makes each unreadable, so toggling flood on hides the risk fill.
    if (visible && map && map.getLayer("risk-grid-fill")) {
      map.setLayoutProperty("risk-grid-fill", "visibility", "none");
      setShowGrid(false);
    }
  };

  return (
    <div className="risk-map-page">
      {/* Backend Unreachable Strip — real, derived from the data-status fetch above */}
      {!backendReachable && (
        <div className="offline-warning-strip">
          <AlertTriangle size={15} />
          <span>
            BACKEND UNREACHABLE — Showing last available cached terrain baseline
            & 500m boundaries
          </span>
        </div>
      )}

      {/* Navigation & Control Toolbar */}
      <header className="risk-toolbar">
        <div className="toolbar-left">
          <button
            type="button"
            className="district-btn"
            onClick={() => onNavigate && onNavigate("HOME")}
            style={{
              padding: "6px 12px",
              background: "rgba(255,255,255,0.06)",
            }}
            title="Return to Landing Page"
          >
            <ArrowLeft size={16} />
            <span>Overview</span>
          </button>

          {/* <div className="toolbar-brand" onClick={() => onNavigate && onNavigate('HOME')}>
            <span className="toolbar-title">NER Safe • 500m Risk Grid</span>
          </div> */}

          {/* District Switcher — single dropdown instead of two always-visible buttons */}
          <div className="district-dropdown-wrap" ref={districtDropdownRef}>
            <button
              type="button"
              className="district-dropdown-trigger"
              onClick={() => setShowDistrictMenu((v) => !v)}
            >
              <MapPin size={14} />
              <span>
                {district} ({DISTRICT_CONFIG[district]?.cells.toLocaleString()}{" "}
                cells)
              </span>
              <ChevronDown
                size={14}
                className={showDistrictMenu ? "chevron-open" : ""}
              />
            </button>
            {showDistrictMenu && (
              <div className="district-dropdown-menu">
                {Object.keys(DISTRICT_CONFIG).map((d) => (
                  <button
                    type="button"
                    key={d}
                    className={`district-dropdown-item ${district === d ? "active" : ""}`}
                    onClick={() => {
                      switchDistrict(d);
                      setShowDistrictMenu(false);
                    }}
                  >
                    <span>{d}</span>
                    <span className="district-dropdown-count">
                      {DISTRICT_CONFIG[d].cells.toLocaleString()} cells
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Single consolidated search: cell ID, district name, or live area/locality autocomplete */}
          <div className="search-input-wrap-container" ref={searchDropdownRef}>
            <form className="search-input-wrap" onSubmit={handleSearchSubmit}>
              <Search size={14} />
              <input
                type="text"
                className="cell-search-input"
                placeholder="Search Area (e.g. Durtlang) or Cell ID (e.g. KOH_01378)"
                value={searchTerm}
                onChange={(e) => {
                  setSearchTerm(e.target.value);
                  setShowAreaSearch(true);
                }}
                onFocus={() => searchTerm.trim() && setShowAreaSearch(true)}
              />
            </form>
            {showAreaSearch && searchTerm.trim().length > 0 && (
              <AreaSearchPanel
                searchTerm={searchTerm}
                district={district}
                onSelectArea={(aid) => {
                  setSelectedAreaId(aid);
                  setShowAreaSearch(false);
                  setSearchTerm("");
                }}
              />
            )}
          </div>
        </div>

        <div className="toolbar-right">
          {isLoadingData && (
            <span
              style={{
                fontSize: 12,
                color: "#38BDF8",
                display: "flex",
                alignItems: "center",
                gap: 6,
              }}
            >
              Loading {district} grid...
            </span>
          )}

          {/* Alert Panel Toggle */}
          <button
            id="btn-toggle-alert-panel"
            type="button"
            onClick={() => setShowAlertPanel((v) => !v)}
            title={
              showAlertPanel ? "Close Alert Dashboard" : "Open Alert Dashboard"
            }
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              padding: "5px 12px",
              background: showAlertPanel
                ? "rgba(239,68,68,0.18)"
                : "rgba(255,255,255,0.06)",
              border: showAlertPanel
                ? "1px solid rgba(239,68,68,0.45)"
                : "1px solid rgba(255,255,255,0.10)",
              borderRadius: 7,
              color: showAlertPanel ? "#EF4444" : "#94A3B8",
              fontSize: 12,
              fontWeight: 600,
              cursor: "pointer",
              transition: "all 0.2s ease",
            }}
          >
            <Bell size={14} />
            Alerts
          </button>

          {/* System Status Pill */}
          <SystemStatusPill
            backendReachable={backendReachable}
            dataStatus={dataStatus}
          />
        </div>
      </header>

      {/* Map Viewport */}
      <main className="risk-map-main" style={{ position: "relative" }}>
        <div ref={mapContainerRef} className="maplibre-container" />

        {/* Floating Layer Controls */}
        <DistrictSelector
          selectedDistrict={district}
          onSelectDistrict={switchDistrict}
          searchTerm={searchTerm}
          onSearchChange={setSearchTerm}
          onSearchSubmit={handleSearchSubmit}
          showGrid={showGrid}
          onToggleGrid={handleToggleGrid}
          showBoundary={showBoundary}
          onToggleBoundary={handleToggleBoundary}
          showHistorical={showHistorical}
          onToggleHistorical={handleToggleHistorical}
          showFlood={showFlood}
          onToggleFlood={handleToggleFlood}
          basemapType={basemapType}
          onChangeBasemap={setBasemapType}
        />

        {/* Risk Legend */}
        <MapLegend dataStatus={dataStatus} />

        {/* Cell Hover Tooltip */}
        {hoveredCell && hoverPosition && !selectedCell && (
          <div
            className="cell-hover-tooltip"
            style={{ left: hoverPosition.x, top: hoverPosition.y }}
          >
            <div className="tooltip-cell-id">
              {hoveredCell.cell_id} ({hoveredCell.district})
            </div>
            <div
              className="tooltip-risk"
              style={{ color: hoveredCell.risk_color }}
            >
              {hoveredCell.risk_badge || hoveredCell.risk_class} • Elev:{" "}
              {hoveredCell.elevation_m || "N/A"}m • Slope:{" "}
              {hoveredCell.slope_deg || "N/A"}°
            </div>
          </div>
        )}

        {/* Cell Details Modal / Drawer */}
        <CellDetailsModal
          cell={selectedCell}
          onClose={() => {
            if (mapRef.current && selectedCell) {
              mapRef.current.setFeatureState(
                { source: "risk-grid", id: selectedCell.cell_id },
                { selected: false },
              );
            }
            setSelectedCell(null);
            if (popupRef.current) {
              popupRef.current.remove();
              popupRef.current = null;
            }
          }}
        />

        {/* Area Risk Intelligence Dashboard Drawer */}
        {selectedAreaId && (
          <AreaRiskDashboard
            areaId={selectedAreaId}
            onClose={() => {
              setSelectedAreaId(null);
              clearAreaHighlight();
            }}
            onSelectCell={(cid) => searchAndSelectCell(cid)}
          />
        )}

        {/* Alert Sidebar Panel */}
        {showAlertPanel && (
          <div
            id="alert-sidebar"
            style={{
              position: "absolute",
              top: 0,
              right: 0,
              width: 390,
              height: "100%",
              background: "rgba(10, 15, 28, 0.97)",
              backdropFilter: "blur(20px)",
              borderLeft: "1px solid rgba(239,68,68,0.20)",
              zIndex: 900,
              display: "flex",
              flexDirection: "column",
              boxShadow: "-6px 0 40px rgba(0,0,0,0.5)",
              animation: "slideInRight 0.25s ease",
            }}
          >
            <AlertPanel district={district} />
          </div>
        )}
      </main>
    </div>
  );
}
