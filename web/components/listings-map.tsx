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

const SOURCE_LABELS: Record<string, string> = {
  phongtro123: "Phongtro123",
  nhatot: "NhaTot",
  mogi: "Mogi",
  fallback: "Fallback"
};

function sourceColor(sourceName: string) {
  if (sourceName === "phongtro123") {
    return "#2563eb";
  }
  if (sourceName === "nhatot") {
    return "#0891b2";
  }
  if (sourceName === "mogi") {
    return "#4f46e5";
  }
  return "#0ea5e9";
}

function sourceLabel(sourceName: string) {
  return SOURCE_LABELS[sourceName] ?? sourceName;
}

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
  return item.primary_image_url || item.thumbnail_url;
}

function cleanDisplayText(value: string | null | undefined) {
  return (value ?? "").replace(/[\u2014\u2013]/g, "-");
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
                  {imageUrl(item) ? <img className="popup-image" src={imageUrl(item) ?? ""} alt={cleanDisplayText(item.title)} /> : null}
                  <span className="popup-badge" style={{ color }}>
                    {sourceLabel(item.source_name)}
                  </span>
                  <strong>{cleanDisplayText(item.title)}</strong>
                  <p>{cleanDisplayText(item.full_address) || "Đang cập nhật địa chỉ"}</p>
                  <p>{formatDistrict(item.district)} - {formatPrecision(item.geocode_precision)}</p>
                  <p>{formatCurrency(item.price_value)}</p>
                  <a href={item.canonical_url} target="_blank" rel="noreferrer">
                    Mở tin gốc
                  </a>
                </div>
              </Popup>
            </CircleMarker>
          );
        })}
    </MapContainer>
  );
}
