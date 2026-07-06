"use client";

import { CircleMarker, MapContainer, Popup, TileLayer, useMap } from "react-leaflet";
import { useEffect } from "react";

import { formatDistrict, formatPrecision } from "../lib/format";
import { Listing } from "../lib/types";

type Props = {
  listings: Listing[];
  selectedListingId: string | null;
  onSelectListing: (listingId: string) => void;
};

const DEFAULT_CENTER: [number, number] = [10.7769, 106.7009];

function FlyToSelection({ listing }: { listing: Listing | undefined }) {
  const map = useMap();

  useEffect(() => {
    if (!listing?.latitude || !listing.longitude) {
      return;
    }
    map.flyTo([listing.latitude, listing.longitude], 14, { duration: 0.75 });
  }, [listing, map]);

  return null;
}

function markerColor(precision: string | null) {
  if (precision === "exact") {
    return "#0f766e";
  }
  if (precision === "district") {
    return "#d97706";
  }
  if (precision === "province") {
    return "#b45309";
  }
  return "#7c2d12";
}

export function ListingsMap({ listings, selectedListingId, onSelectListing }: Props) {
  const centered = listings.find((item) => item.id === selectedListingId && item.latitude && item.longitude) ||
    listings.find((item) => item.latitude && item.longitude);
  const center: [number, number] = centered ? [centered.latitude as number, centered.longitude as number] : DEFAULT_CENTER;
  const selectedListing = listings.find((item) => item.id === selectedListingId);

  return (
    <MapContainer center={center} zoom={12} scrollWheelZoom className="map">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <FlyToSelection listing={selectedListing} />
      {listings
        .filter((item) => item.latitude && item.longitude)
        .map((item) => (
          <CircleMarker
            key={item.id}
            center={[item.latitude as number, item.longitude as number]}
            radius={item.id === selectedListingId ? 9 : 6}
            pathOptions={{
              color: markerColor(item.geocode_precision),
              fillColor: markerColor(item.geocode_precision),
              fillOpacity: item.id === selectedListingId ? 0.95 : 0.72,
              weight: item.id === selectedListingId ? 3 : 1
            }}
            eventHandlers={{
              click: () => onSelectListing(item.id)
            }}
          >
            <Popup>
              <div className="popup">
                <span className="popup-badge">{item.geocode_precision ?? "none"}</span>
                <strong>{item.title}</strong>
                <p>{item.full_address ?? "Dang cap nhat dia chi"}</p>
                <p>{formatDistrict(item.district)} · {formatPrecision(item.geocode_precision)}</p>
                <p>
                  {item.price_value ? `${item.price_value.toLocaleString("vi-VN")} VND` : "Gia dang cap nhat"}
                </p>
                <a href={item.canonical_url} target="_blank" rel="noreferrer">
                  Mo tin goc
                </a>
              </div>
            </Popup>
          </CircleMarker>
        ))}
    </MapContainer>
  );
}
