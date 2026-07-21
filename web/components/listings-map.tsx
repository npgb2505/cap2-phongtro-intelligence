"use client";

/* Popup thumbnails are remote crawler assets rendered inside Leaflet's DOM. */
/* eslint-disable @next/next/no-img-element */

import L from "leaflet";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Circle, CircleMarker, MapContainer, Popup, TileLayer, useMap, useMapEvents } from "react-leaflet";

import { formatDistrict } from "../lib/format";
import { MAP_LOCATION_LABELS, MapLocationGroup, MapLocationLevel } from "../lib/map-locations";
import { Listing } from "../lib/types";

type Props = {
  groups: MapLocationGroup[];
  selectedListingId: string | null;
  focusCoordinate: [number, number] | null;
  onSelectListing: (listingId: string) => void;
  onRenderStats: (markerCount: number, listingCount: number) => void;
};

type ViewportRect = {
  south: number;
  west: number;
  north: number;
  east: number;
};

const DEFAULT_CENTER: [number, number] = [10.7769, 106.7009];
const MAX_VIEWPORT_MARKERS = 1000;
const LOCATION_COLORS: Record<MapLocationLevel, string> = {
  exact: "#2563eb",
  street: "#0891b2",
  district: "#4f46e5",
  province: "#64748b"
};
const LOCATION_UNCERTAINTY_RADIUS: Record<MapLocationLevel, number> = {
  exact: 0,
  street: 350,
  district: 2500,
  province: 12000
};

function formatCurrency(value: number | null) {
  if (!value || value < 1000) {
    return "Liên hệ";
  }
  if (value >= 1_000_000) {
    return `${(value / 1_000_000).toLocaleString("vi-VN", { maximumFractionDigits: 1 })} triệu/tháng`;
  }
  return `${value.toLocaleString("vi-VN")} VND`;
}

function imageUrl(item: Listing) {
  const candidate = item.primary_image_url || item.thumbnail_url;
  return candidate && /^https?:\/\//i.test(candidate) && !/(?:thumb_default|no[-_]image|placeholder|default[-_]image)/i.test(candidate)
    ? candidate
    : null;
}

function cleanDisplayText(value: string | null | undefined) {
  return (value ?? "").replace(/[\u2014\u2013]/g, "-");
}

function googleMapsSearchUrl(item: Listing) {
  const query = item.full_address || item.street_address || [item.district, item.province].filter(Boolean).join(", ");
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query || "Việt Nam")}`;
}

function locationExplanation(level: MapLocationLevel) {
  if (level === "exact") {
    return "Marker dùng tọa độ nguồn cho địa chỉ có số nhà.";
  }
  if (level === "street") {
    return "Vùng nét đứt biểu thị khu vực ước lượng quanh tuyến đường, không phải số nhà chính xác.";
  }
  if (level === "district") {
    return "Vùng nét đứt biểu thị khu vực ước lượng quanh trung tâm quận huyện.";
  }
  return "Vùng nét đứt biểu thị khu vực ước lượng quanh trung tâm tỉnh thành.";
}

function ResizeMap() {
  const map = useMap();

  useEffect(() => {
    let animationFrame = 0;
    const container = map.getContainer();
    const invalidate = () => {
      window.cancelAnimationFrame(animationFrame);
      animationFrame = window.requestAnimationFrame(() => map.invalidateSize({ pan: false }));
    };
    const observer = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(invalidate);

    observer?.observe(container);
    window.addEventListener("resize", invalidate);
    invalidate();
    const followUp = window.setTimeout(invalidate, 260);

    return () => {
      observer?.disconnect();
      window.removeEventListener("resize", invalidate);
      window.clearTimeout(followUp);
      window.cancelAnimationFrame(animationFrame);
    };
  }, [map]);

  return null;
}

function ViewportTracker({ onChange }: { onChange: (viewport: ViewportRect) => void }) {
  const map = useMap();
  const emitViewport = useCallback(() => {
    const bounds = map.getBounds();
    onChange({
      south: bounds.getSouth(),
      west: bounds.getWest(),
      north: bounds.getNorth(),
      east: bounds.getEast()
    });
  }, [map, onChange]);
  useMapEvents({
    moveend: emitViewport,
    zoomend: emitViewport
  });

  useEffect(() => {
    const animationFrame = window.requestAnimationFrame(emitViewport);
    return () => window.cancelAnimationFrame(animationFrame);
  }, [emitViewport]);

  return null;
}

function FitVisibleLocations({
  groups,
  selectedGroup,
  selectedListingId,
  focusCoordinate
}: {
  groups: MapLocationGroup[];
  selectedGroup: MapLocationGroup | undefined;
  selectedListingId: string | null;
  focusCoordinate: [number, number] | null;
}) {
  const map = useMap();
  const bounds = useMemo(() => {
    const points = groups.map((group) => [group.latitude, group.longitude] as [number, number]);
    return points.length > 1 ? L.latLngBounds(points) : null;
  }, [groups]);

  useEffect(() => {
    let animationFrame = 0;
    const moveTo = (coordinate: [number, number], zoom: number) => {
      if (!coordinate.every(Number.isFinite)) {
        return;
      }
      animationFrame = window.requestAnimationFrame(() => {
        map.stop();
        map.invalidateSize({ pan: false });
        map.setView(coordinate, zoom, { animate: true });
      });
    };

    if (selectedGroup) {
      const zoomByLevel: Record<MapLocationLevel, number> = { exact: 18, street: 17, district: 14, province: 11 };
      moveTo([selectedGroup.latitude, selectedGroup.longitude], zoomByLevel[selectedGroup.level]);
    } else if (focusCoordinate) {
      moveTo(focusCoordinate, 15);
    } else if (bounds) {
      animationFrame = window.requestAnimationFrame(() => {
        map.stop();
        map.invalidateSize({ pan: false });
        map.fitBounds(bounds, { padding: [34, 34], maxZoom: 12, animate: true });
      });
    }

    return () => window.cancelAnimationFrame(animationFrame);
  }, [bounds, focusCoordinate, map, selectedGroup, selectedListingId]);

  return null;
}

export function ListingsMap({ groups, selectedListingId, focusCoordinate, onSelectListing, onRenderStats }: Props) {
  const [viewport, setViewport] = useState<ViewportRect | null>(null);
  const selectedGroup = groups.find((group) =>
    selectedListingId ? group.listingIds.includes(selectedListingId) : false
  );
  const handleViewportChange = useCallback((nextViewport: ViewportRect) => {
    setViewport((current) => {
      if (
        current &&
        Math.abs(current.south - nextViewport.south) < 0.00001 &&
        Math.abs(current.west - nextViewport.west) < 0.00001 &&
        Math.abs(current.north - nextViewport.north) < 0.00001 &&
        Math.abs(current.east - nextViewport.east) < 0.00001
      ) {
        return current;
      }
      return nextViewport;
    });
  }, []);
  const renderedGroups = useMemo(() => {
    if (!viewport) {
      return groups.slice(0, MAX_VIEWPORT_MARKERS);
    }
    const latitudePadding = (viewport.north - viewport.south) * 0.2;
    const longitudePadding = (viewport.east - viewport.west) * 0.2;
    const south = viewport.south - latitudePadding;
    const north = viewport.north + latitudePadding;
    const west = viewport.west - longitudePadding;
    const east = viewport.east + longitudePadding;
    const centerLatitude = (viewport.south + viewport.north) / 2;
    const centerLongitude = (viewport.west + viewport.east) / 2;
    const candidates = groups
      .filter((group) =>
        group.latitude >= south &&
        group.latitude <= north &&
        group.longitude >= west &&
        group.longitude <= east
      )
      .sort((first, second) => {
        const firstSelected = selectedListingId ? first.listingIds.includes(selectedListingId) : false;
        const secondSelected = selectedListingId ? second.listingIds.includes(selectedListingId) : false;
        if (firstSelected !== secondSelected) {
          return firstSelected ? -1 : 1;
        }
        const firstDistance = Math.hypot(first.latitude - centerLatitude, first.longitude - centerLongitude);
        const secondDistance = Math.hypot(second.latitude - centerLatitude, second.longitude - centerLongitude);
        return firstDistance - secondDistance;
      });
    return candidates.slice(0, MAX_VIEWPORT_MARKERS);
  }, [groups, selectedListingId, viewport]);

  useEffect(() => {
    onRenderStats(
      renderedGroups.length,
      renderedGroups.reduce((total, group) => total + group.count, 0)
    );
  }, [onRenderStats, renderedGroups]);

  const centered = selectedGroup ?? groups[0];
  const center: [number, number] = centered
    ? [centered.latitude, centered.longitude]
    : focusCoordinate ?? DEFAULT_CENTER;

  return (
    <MapContainer center={center} zoom={11} scrollWheelZoom preferCanvas className="map">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <ResizeMap />
      <ViewportTracker onChange={handleViewportChange} />
      <FitVisibleLocations
        groups={groups}
        selectedGroup={selectedGroup}
        selectedListingId={selectedListingId}
        focusCoordinate={focusCoordinate}
      />
      {selectedGroup && selectedGroup.level !== "exact" ? (
        <Circle
          center={[selectedGroup.latitude, selectedGroup.longitude]}
          radius={LOCATION_UNCERTAINTY_RADIUS[selectedGroup.level]}
          pathOptions={{
            color: LOCATION_COLORS[selectedGroup.level],
            fillColor: LOCATION_COLORS[selectedGroup.level],
            fillOpacity: 0.1,
            opacity: 0.5,
            weight: 2,
            dashArray: "7 6"
          }}
          interactive={false}
        />
      ) : null}
      {renderedGroups.map((group) => {
        const item = group.representative;
        const selected = selectedListingId ? group.listingIds.includes(selectedListingId) : false;
        const color = LOCATION_COLORS[group.level];
        const radius = selected ? 11 : Math.min(18, 5 + Math.log2(group.count + 1) * 1.8);
        return (
          <CircleMarker
            key={group.id}
            center={[group.latitude, group.longitude]}
            radius={radius}
            pathOptions={{
              color,
              fillColor: color,
              fillOpacity: selected ? 0.94 : group.level === "exact" ? 0.72 : group.level === "street" ? 0.62 : 0.48,
              opacity: selected ? 1 : 0.82,
              weight: selected ? 4 : group.count > 1 ? 2 : 1
            }}
            eventHandlers={{ click: () => onSelectListing(item.id) }}
          >
            <Popup>
              <div className="popup">
                {imageUrl(item) ? (
                  <img className="popup-image" src={imageUrl(item) ?? ""} alt={cleanDisplayText(item.title)} />
                ) : null}
                <span className="popup-badge" style={{ color }}>
                  {MAP_LOCATION_LABELS[group.level]}
                </span>
                <strong>
                  {group.count > 1
                    ? `${group.count.toLocaleString("vi-VN")} tin cùng mức vị trí`
                    : cleanDisplayText(item.title)}
                </strong>
                {group.count > 1 ? <p>Ví dụ: {cleanDisplayText(item.title)}</p> : null}
                <p>{cleanDisplayText(item.full_address) || "Đang cập nhật địa chỉ"}</p>
                <p>{formatDistrict(item.district)}</p>
                <p className="popup-confidence">{locationExplanation(group.level)}</p>
                <p>{formatCurrency(item.price_value)}</p>
                <a href={googleMapsSearchUrl(item)} target="_blank" rel="noreferrer">
                  Kiểm tra địa chỉ trên Google Maps
                </a>
              </div>
            </Popup>
          </CircleMarker>
        );
      })}
    </MapContainer>
  );
}
