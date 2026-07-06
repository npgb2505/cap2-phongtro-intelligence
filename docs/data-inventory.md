# Rental Source Data Inventory

This document captures the fields verified from the live Phongtro123 website on 2026-06-29 and maps them to the current local crawler. The ETL now also includes source adapters for NhaTot and BatDongSan through public listing APIs.

## Configured sources

- `phongtro123`: dedicated parser for search and detail pages.
- `alonhadat`: generic parser using listing links, Open Graph metadata, detail text, and regex fallback.
- `thuephongtro`: generic parser using listing links, Open Graph metadata, detail text, and regex fallback.
- `nhatot`: JSON API parser through the public ChoTot listing gateway for category `1050` (`Phòng trọ`); page 1 returns 20 ads and the API reports `total=10000`.
- `batdongsan`: mobile map API parser through `https://apimap.batdongsan.com.vn/api/p_sync`, using `ptype=49` and `cate=0` for the broader `Nhà đất cho thuê` feed because the narrow `cate=57` room-rental feed currently exposes only a few active posts; HTML category pages still return a Cloudflare challenge, so the crawler uses the app API payload instead.
- `mogi`: direct search-result parser for `https://mogi.vn/thue-phong-tro-nha-tro`; the listing page reports tens of thousands of room-rental results and currently provides clean card-level fields without detail-page crawling.

Every normalized row includes `source_name`, `source_post_id`, `canonical_url`, and `content_hash` so merged outputs can be deduplicated and traced back to the source site.

## Search/list page fields

Verified from the Ho Chi Minh search page in the in-app browser:

- listing detail URL
- listing title
- price text
- area text
- district/province label
- teaser description
- poster display name
- relative posted time
- primary contact phone shown on card
- gallery image count
- multiple thumbnail image URLs
- sort mode URLs such as `orderby=moi-nhat`
- province and district filter links

## Detail page fields

Verified from a live detail page (`pr689447`) in the in-app browser:

- canonical listing URL
- source listing id (`Mã tin`)
- title
- description
- district breadcrumb
- province breadcrumb
- full street address
- published time (`Ngày đăng`)
- expiry time (`Ngày hết hạn`)
- poster/author name
- primary phone number
- Zalo link
- image gallery URLs
- structured data from JSON-LD:
  - `datePublished`
  - `dateModified`
  - `author.name`
  - `address.streetAddress`
  - `address.addressLocality`
  - `priceRange`
  - `telephone`
- embedded Google Maps iframe query with address text

## Current normalized crawler fields

The local crawler now writes these normalized fields:

- `source_name`
- `source_post_id`
- `canonical_url`
- `title`
- `description`
- `price_text`
- `price_value`
- `area_text`
- `area_m2`
- `full_address`
- `province`
- `district`
- `latitude`
- `longitude`
- `contact_name`
- `contact_phone`
- `contact_zalo_url`
- `posted_at`
- `expired_at`
- `amenities`
- `image_urls`
- `content_hash`

## Gaps still worth filling

- `latitude` and `longitude` are still null because the site exposes an embeddable map query, not direct coordinates.
- A future AWS-first geocoding step should resolve coordinates from `full_address` using Amazon Location Service so the frontend map can render listing markers.
- The detail page likely contains additional media and surrounding recommendations that we may store later in separate raw/derived tables instead of bloating the core listing table.
