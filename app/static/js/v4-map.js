
/* =========================================================
   CIVICTRACK V4 — INTERACTIVE MAP ENGINE
   Leaflet + OpenStreetMap + Nominatim Reverse Geocoding
   ========================================================= */

(() => {
    "use strict";

    const mapElement = document.getElementById(
        "complaint-location-map"
    );

    if (!mapElement) return;

    const locationInput = document.getElementById("location");
    const latitudeInput = document.getElementById("latitude");
    const longitudeInput = document.getElementById("longitude");

    const statusElement = document.getElementById(
        "map-selection-status"
    );

    const locateButton = document.getElementById(
        "map-use-current-location"
    );

    const clearButton = document.getElementById(
        "map-clear-selection"
    );

    if (
        !locationInput ||
        !latitudeInput ||
        !longitudeInput ||
        !statusElement
    ) {
        console.error(
            "CivicTrack map: Required form elements are missing."
        );
        return;
    }

    if (!window.L) {
        statusElement.textContent =
            "The map library could not load. Check your internet connection.";

        console.error("CivicTrack map: Leaflet is unavailable.");
        return;
    }

    /* =====================================================
       MAP INITIALIZATION
       ===================================================== */

    const map = L.map(mapElement, {
        zoomControl: true,
        scrollWheelZoom: false,
        doubleClickZoom: true,
        minZoom: 3,
        maxZoom: 19
    }).setView([20.5937, 78.9629], 5);

    L.tileLayer(
        "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
        {
            minZoom: 3,
            maxZoom: 19,

            attribution:
                '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap contributors</a>'
        }
    ).addTo(map);

    /* =====================================================
       LOCATION STATE
       ===================================================== */

    let selectedMarker = null;

    let geocodeTimer = null;
    let activeRequest = null;
    let requestNumber = 0;
    let lastRequestTime = 0;

    const GEOCODING_DELAY = 700;
    const MIN_REQUEST_INTERVAL = 1100;

    function updateCoordinates(position) {

        const latitude = Number(position.lat.toFixed(6));
        const longitude = Number(position.lng.toFixed(6));

        latitudeInput.value = String(latitude);
        longitudeInput.value = String(longitude);

        return { latitude, longitude };
    }

    /* =====================================================
       REVERSE GEOCODING
       OpenStreetMap Nominatim
       ===================================================== */

    function cancelGeocoding() {

        if (geocodeTimer !== null) {
            clearTimeout(geocodeTimer);
            geocodeTimer = null;
        }

        if (activeRequest) {
            activeRequest.abort();
            activeRequest = null;
        }

        requestNumber++;
    }

    function getReadableAddress(data) {

        if (!data || !data.address) {
            return data?.display_name || "";
        }

        const address = data.address;

        const parts = [];

        const road =
            address.road ||
            address.pedestrian ||
            address.residential ||
            address.path;

        const neighbourhood =
            address.neighbourhood ||
            address.suburb ||
            address.quarter;

        const locality =
            address.city ||
            address.town ||
            address.village ||
            address.municipality;

        const district =
            address.city_district ||
            address.county ||
            address.district;

        const state = address.state;

        const country = address.country;

        [
            road,
            neighbourhood,
            locality,
            district,
            state,
            country
        ].forEach(part => {

            if (
                part &&
                !parts.some(
                    existing =>
                        existing.toLowerCase() === part.toLowerCase()
                )
            ) {
                parts.push(part);
            }

        });

        return parts.length > 0
            ? parts.join(", ")
            : data.display_name || "";
    }

    async function reverseGeocode(
        latitude,
        longitude,
        currentRequest
    ) {

        if (activeRequest) {
            activeRequest.abort();
        }

        const controller = new AbortController();

        activeRequest = controller;

        const url = new URL(
            "https://nominatim.openstreetmap.org/reverse"
        );

        url.searchParams.set("format", "jsonv2");
        url.searchParams.set("lat", String(latitude));
        url.searchParams.set("lon", String(longitude));
        url.searchParams.set("zoom", "18");
        url.searchParams.set("addressdetails", "1");

        try {

            const response = await fetch(url, {
                method: "GET",
                headers: {
                    "Accept": "application/json"
                },
                signal: controller.signal
            });

            if (!response.ok) {
                throw new Error(
                    `Address service returned HTTP ${response.status}`
                );
            }

            const data = await response.json();

            if (currentRequest !== requestNumber) return;

            const readableAddress =
                getReadableAddress(data);

            if (!readableAddress) {
                throw new Error("No readable address was returned.");
            }

            locationInput.value = readableAddress;

            statusElement.textContent =
                `Address found: ${readableAddress}. You can drag the marker to adjust the location.`;

        } catch (error) {

            if (error.name === "AbortError") return;

            if (currentRequest !== requestNumber) return;

            console.error(
                "CivicTrack reverse geocoding error:",
                error
            );

            locationInput.value =
                `Coordinates: ${latitude}, ${longitude}`;

            statusElement.textContent =
                "Address lookup failed. Your exact map coordinates have been retained.";

        } finally {

            if (activeRequest === controller) {
                activeRequest = null;
            }

        }
    }

    function scheduleReverseGeocoding(
        latitude,
        longitude
    ) {

        cancelGeocoding();

        const currentRequest = requestNumber;

        locationInput.value = "Finding address...";

        statusElement.textContent =
            "Your location is selected. Looking up the street address...";

        geocodeTimer = setTimeout(() => {

            const elapsed =
                Date.now() - lastRequestTime;

            const remaining =
                Math.max(
                    0,
                    MIN_REQUEST_INTERVAL - elapsed
                );

            geocodeTimer = setTimeout(() => {

                if (currentRequest !== requestNumber) return;

                lastRequestTime = Date.now();

                reverseGeocode(
                    latitude,
                    longitude,
                    currentRequest
                );

            }, remaining);

        }, GEOCODING_DELAY);
    }

    /* =====================================================
       UPDATE LOCATION FIELDS
       ===================================================== */

    function updateLocationFields(position) {

        const coordinates = updateCoordinates(position);

        scheduleReverseGeocoding(
            coordinates.latitude,
            coordinates.longitude
        );
    }

    /* =====================================================
       MARKER SELECTION
       ===================================================== */

    function setSelection(position) {

        if (
            !Number.isFinite(position.lat) ||
            !Number.isFinite(position.lng) ||
            position.lat < -90 ||
            position.lat > 90 ||
            position.lng < -180 ||
            position.lng > 180
        ) {

            statusElement.textContent =
                "Invalid map location. Please select another point.";

            return;
        }

        if (!selectedMarker) {

            selectedMarker = L.marker(position, {
                draggable: true,
                keyboard: true,
                title: "Selected complaint location",
                alt: "Selected complaint location"
            }).addTo(map);

            selectedMarker.bindPopup(
                "<strong>Complaint location</strong><br>Drag this marker to adjust."
            );

            selectedMarker.on("dragend", () => {

                updateLocationFields(
                    selectedMarker.getLatLng()
                );

            });

        } else {

            selectedMarker.setLatLng(position);

        }

        updateLocationFields(position);
    }

    /* =====================================================
       MAP CLICK
       ===================================================== */

    map.on("click", event => {

        setSelection(event.latlng);

    });

    /* =====================================================
       CURRENT LOCATION
       ===================================================== */

    if (locateButton) {

        locateButton.addEventListener("click", () => {

            if (!navigator.geolocation) {

                statusElement.textContent =
                    "Your browser does not support location services.";

                return;
            }

            locateButton.disabled = true;
            locateButton.textContent = "Locating...";

            statusElement.textContent =
                "Requesting permission to access your location...";

            navigator.geolocation.getCurrentPosition(

                position => {

                    const coordinates = L.latLng(
                        position.coords.latitude,
                        position.coords.longitude
                    );

                    map.setView(coordinates, 17);

                    setSelection(coordinates);

                    locateButton.disabled = false;
                    locateButton.textContent =
                        "Use my current location";

                },

                error => {

                    const messages = {
                        1: "Location permission was denied. Select a point manually.",
                        2: "Your current location is unavailable.",
                        3: "Location request timed out. Try again."
                    };

                    statusElement.textContent =
                        messages[error.code] ||
                        "Unable to determine your location.";

                    locateButton.disabled = false;
                    locateButton.textContent =
                        "Use my current location";

                },

                {
                    enableHighAccuracy: true,
                    timeout: 12000,
                    maximumAge: 60000
                }
            );

        });

    }

    /* =====================================================
       CLEAR SELECTION
       ===================================================== */

    function clearSelection() {

        cancelGeocoding();

        if (selectedMarker) {

            map.removeLayer(selectedMarker);
            selectedMarker = null;

        }

        latitudeInput.value = "";
        longitudeInput.value = "";
        locationInput.value = "";

        statusElement.textContent =
            "No location selected. Tap the map to choose the problem location.";

    }

    if (clearButton) {

        clearButton.addEventListener(
            "click",
            clearSelection
        );

    }

    /* =====================================================
       FORM RESET
       ===================================================== */

    const form = mapElement.closest("form");

    if (form) {

        form.addEventListener("reset", () => {

            requestAnimationFrame(clearSelection);

        });

    }

    /* =====================================================
       PUBLIC MAP API
       Used by CivicTrack app.js during submission.
       ===================================================== */

    window.CivicTrackMap = Object.freeze({

        getSelection() {

            if (
                !latitudeInput.value ||
                !longitudeInput.value
            ) {
                return null;
            }

            const latitude = Number(latitudeInput.value);
            const longitude = Number(longitudeInput.value);

            if (
                !Number.isFinite(latitude) ||
                !Number.isFinite(longitude)
            ) {
                return null;
            }

            return {
                latitude,
                longitude,
                address: locationInput.value
            };

        },

        clearSelection

    });

    /* =====================================================
       INITIAL MAP LAYOUT
       ===================================================== */

    map.whenReady(() => {

        requestAnimationFrame(() => {
            map.invalidateSize();
        });

    });

})();

