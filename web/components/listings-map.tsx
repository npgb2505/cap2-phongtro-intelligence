"use client";

import { CircleMarker, MapContainer, Popup, TileLayer, useMap } from "react-leaflet";
import { useEffect, useMemo } from "react";
import L from "leaflet";

import { formatDistrict, formatPrecision } from "../lib/format";
import { Listing } from "../lib/types";

type Props = {
  listings: Listing[];
  selectedListingId: string | null;
  onSelectListing: (listingId: string) => void;
};

const DEFAULT_CENTER: [number, number] = [10.7769, 106.7009];

function sourceColor(sourceName: string) {
  if (sourceName === "phongtro123") {
    return "#0f766e";
  }
  if (sourceName === "nhatot") {
    return "#2563eb";
  }
  if (sourceName === "mogi") {
    return "#db2777";
  }
  return "#f59e0b";
}

function FitVisibleListings({ listings, selectedListing }: { listings: Listing[]; selectedListing: Listing | undefined }) {
  const map = useMap();

  const bounds = useMemo(() => {
    const points = listings
      .filter((item) => item.latitude && item.longitude)
      .slice(0, 900)
      .map((item) => [item.latitude as number, item.longitude as number] as [number, number]);
    return points.length > 1 ? L.latLngBounds(points) : null;
  }, [listings]);

  useEffect(() => {
    if (selectedListing?.latitude && selectedListing.longitude) {
      map.flyTo([selectedListing.latitude, selectedListing.longitude], 14, { duration: 0.7 });
      return;
    }
    if (bounds) {
      map.fitBounds(bounds, { padding: [34, 34], maxZoom: 12 });
    }
  }, [bounds, map, selectedListing]);

  return null;
}

export function ListingsMap({ listings, selectedListingId, onSelectListing }: Props) {
  const selectedListing = listings.find((item) => item.id === selectedListingId);
  const centered =
    selectedListing ||
    listings.find((item) => item.latitude && item.longitude);
  const center: [number, number] = centered?.latitude && centered.longitude
    ? [centered.latitude, centered.longitude]
    : DEFAULT_CENTER;

  return (
    <MapContainer center={center} zoom={11} scrollWheelZoom className="map">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <FitVisibleListings listings={listings} selectedListing={selectedListing} />
      {listings
        .filter((item) => item.latitude && item.longitude)
        .map((item) => {
          const selected = item.id === selectedListingId;
          const color = sourceColor(item.source_name);
          return (
            <CircleMarker
              key={item.id}
              center={[item.latitude as number, item.longitude as number]}
              radius={selected ? 10 : 5}
              pathOptions={{
                color,
                fillColor: color,
                fillOpacity: selected ? 0.94 : 0.62,
                opacity: selected ? 1 : 0.78,
                weight: selected ? 4 : 1
              }}
              eventHandlers={{
                click: () => onSelectListing(item.id)
              }}
            >
              <Popup>
                <div className="popup">
                  <span className="popup-badge" style={{ color }}>
                    {item.source_name}
                  </span>
                  <strong>{item.title}</strong>
                  <p>{item.full_address ?? "Dang cap nhat dia chi"}</p>
                  <p>{formatDistrict(item.district)} - {formatPrecision(item.geocode_precision)}</p>
                  <p>{item.price_value ? `${item.price_value.toLocaleString("vi-VN")} VND` : "Gia dang cap nhat"}</p>
                  <a href={item.canonical_url} target="_blank" rel="noreferrer">
                    Mo tin goc
                  </a>
                </div>
              </Popup>
            </CircleMarker>
          );
        })}
    </MapContainer>
  );
}
