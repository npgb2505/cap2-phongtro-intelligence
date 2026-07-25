const DISTRICT_ALIASES: Record<string, string> = {
  "quan 1": "Quận 1",
  "quan 2": "Quận 2",
  "quan 3": "Quận 3",
  "quan 4": "Quận 4",
  "quan 5": "Quận 5",
  "quan 6": "Quận 6",
  "quan 7": "Quận 7",
  "quan 8": "Quận 8",
  "quan 9": "Quận 9",
  "quan 10": "Quận 10",
  "quan 11": "Quận 11",
  "quan 12": "Quận 12",
  "go vap": "Gò Vấp",
  "binh thanh": "Bình Thạnh",
  "tan binh": "Tân Bình",
  "tan phu": "Tân Phú",
  "phu nhuan": "Phú Nhuận",
  "huyen hoc mon": "Huyện Hóc Môn",
  "huyen cu chi": "Huyện Củ Chi",
  "huyen nha be": "Huyện Nhà Bè",
  "huyen binh chanh": "Huyện Bình Chánh",
  "thanh pho da lat": "Thành phố Đà Lạt",
  "thanh pho hue": "Thành phố Huế",
  "thanh pho vung tau": "Thành phố Vũng Tàu",
  "thanh pho thuan an": "Thành phố Thuận An",
  "thanh pho di an": "Thành phố Dĩ An",
};

const PRECISION_LABELS: Record<string, string> = {
  exact: "Đã khớp số nhà và tên đường",
  street: "Điểm tham chiếu trên tuyến đường",
  district: "Điểm đại diện cấp quận huyện",
  province: "Điểm đại diện cấp tỉnh thành",
  none: "Chưa định vị",
};

function foldText(value: string) {
  return value
    .toLowerCase()
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .replace(/đ/g, "d")
    .replace(/\s+/g, " ")
    .trim();
}

export function formatDistrict(value: string | null | undefined) {
  if (!value) {
    return "Chưa rõ khu vực";
  }
  return DISTRICT_ALIASES[foldText(value)] ?? value;
}

export function formatPrecision(value: string | null | undefined) {
  if (!value) {
    return PRECISION_LABELS.none;
  }
  return PRECISION_LABELS[value] ?? value;
}
