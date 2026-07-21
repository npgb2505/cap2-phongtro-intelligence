import { Listing } from "./types";

export type MapLocationLevel = "exact" | "street" | "district" | "province";

export type MapLocationGroup = {
  id: string;
  level: MapLocationLevel;
  latitude: number;
  longitude: number;
  count: number;
  listingIds: string[];
  representative: Listing;
};

const LEVEL_RANK: Record<MapLocationLevel, number> = {
  exact: 0,
  street: 1,
  district: 2,
  province: 3
};

export const MAP_LOCATION_LABELS: Record<MapLocationLevel, string> = {
  exact: "Địa chỉ có số nhà",
  street: "Vị trí trên tuyến đường",
  district: "Trung tâm quận huyện",
  province: "Trung tâm tỉnh thành"
};

function foldText(value: string | null | undefined) {
  return (value ?? "")
    .toLocaleLowerCase("vi-VN")
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .replace(/đ/g, "d")
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function coordinateKey(item: Listing) {
  if (!Number.isFinite(item.latitude) || !Number.isFinite(item.longitude)) {
    return null;
  }
  return `${(item.latitude as number).toFixed(5)},${(item.longitude as number).toFixed(5)}`;
}

function hasHouseNumber(value: string | null | undefined) {
  return /^\s*\d+[a-zA-Z]?(?:[\/-]\d+[a-zA-Z]?)*\b/.test(value ?? "");
}

export function listingAddressLevel(item: Listing): MapLocationLevel | null {
  if (item.geocode_precision === "exact") {
    if (hasHouseNumber(item.street_address)) {
      return "exact";
    }
    return item.street_address ? "street" : item.district ? "district" : item.province ? "province" : null;
  }
  if (item.geocode_precision === "district") {
    return "district";
  }
  if (item.geocode_precision === "province") {
    return "province";
  }
  return null;
}

function locationLevel(item: Listing, coordinateFrequency: number): MapLocationLevel | null {
  if (item.geocode_precision === "exact") {
    if (coordinateFrequency === 1 && hasHouseNumber(item.street_address)) {
      return "exact";
    }
    if (item.street_address) {
      return "street";
    }
    return item.district ? "district" : item.province ? "province" : null;
  }
  if (item.geocode_precision === "district") {
    return "district";
  }
  if (item.geocode_precision === "province") {
    return "province";
  }
  return null;
}

function groupKey(item: Listing, level: MapLocationLevel, coordinateFrequency: number) {
  if (level === "exact") {
    return `exact:${foldText(item.map_reference_address || item.full_address)}:${coordinateKey(item)}`;
  }
  if (level === "street") {
    if (coordinateFrequency > 1) {
      return `street-coordinate:${coordinateKey(item)}`;
    }
    return `street:${foldText(item.street_address)}:${foldText(item.district)}:${foldText(item.province)}`;
  }
  if (level === "district") {
    return `district:${foldText(item.district)}:${foldText(item.province)}`;
  }
  return `province:${foldText(item.province)}`;
}

export function buildMapLocationGroups(items: Listing[]) {
  const locatedItems = items.filter((item) => Number.isFinite(item.latitude) && Number.isFinite(item.longitude));
  const coordinateCounts = locatedItems.reduce<Map<string, number>>((counts, item) => {
    const key = coordinateKey(item);
    if (key) {
      counts.set(key, (counts.get(key) ?? 0) + 1);
    }
    return counts;
  }, new Map());

  const groups = new Map<
    string,
    {
      id: string;
      level: MapLocationLevel;
      latitudeTotal: number;
      longitudeTotal: number;
      count: number;
      listingIds: string[];
      representative: Listing;
    }
  >();

  for (const item of locatedItems) {
    const coordinate = coordinateKey(item);
    if (!coordinate) {
      continue;
    }
    const frequency = coordinateCounts.get(coordinate) ?? 1;
    const level = locationLevel(item, frequency);
    if (!level) {
      continue;
    }
    const key = groupKey(item, level, frequency);
    const existing = groups.get(key);
    if (existing) {
      existing.latitudeTotal += item.latitude as number;
      existing.longitudeTotal += item.longitude as number;
      existing.count += 1;
      existing.listingIds.push(item.id);
      continue;
    }
    groups.set(key, {
      id: key,
      level,
      latitudeTotal: item.latitude as number,
      longitudeTotal: item.longitude as number,
      count: 1,
      listingIds: [item.id],
      representative: item
    });
  }

  return Array.from(groups.values())
    .map<MapLocationGroup>((group) => ({
      id: group.id,
      level: group.level,
      latitude: group.latitudeTotal / group.count,
      longitude: group.longitudeTotal / group.count,
      count: group.count,
      listingIds: group.listingIds,
      representative: group.representative
    }))
    .sort((first, second) => LEVEL_RANK[first.level] - LEVEL_RANK[second.level] || second.count - first.count);
}

export function locationLevelCounts(groups: MapLocationGroup[]) {
  return groups.reduce<Record<MapLocationLevel, number>>(
    (counts, group) => {
      counts[group.level] += group.count;
      return counts;
    },
    { exact: 0, street: 0, district: 0, province: 0 }
  );
}
