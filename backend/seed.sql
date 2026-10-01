-- ============================================================
-- SIH PS26193 — PROCUREMENT CENTER SEED DATA
-- 40 distinct real mandi/APMC locations
--
-- Run schema.sql first.
--
-- Real-world:
--   * Mandi/APMC names and locations
--   * 2026-27 MSP reference values
--
-- Demo/application:
--   * open_date
--   * close_date
--   * is_active
--
-- created_at is intentionally omitted because schema.sql
-- provides DEFAULT now().
--
-- Safe to re-run because the fixed UUIDs are used with
-- ON CONFLICT (id) DO UPDATE.
-- ============================================================

INSERT INTO procurement_centers
(
    id,
    name,
    location,
    crop_type,
    msp_rate,
    open_date,
    close_date,
    is_active
)
VALUES

-- ============================================================
-- HARYANA
-- ============================================================

(
    'c0000000-0000-0000-0000-000000000001',
    'New Grain Market Main, Karnal',
    'Karnal, Haryana',
    'Wheat',
    2585.00,
    '2026-04-01',
    '2026-05-15',
    false
),

(
    'c0000000-0000-0000-0000-000000000002',
    'New Grain Market, Rohtak',
    'Rohtak, Haryana',
    'Gram',
    5875.00,
    '2026-03-01',
    '2026-04-30',
    false
),

(
    'c0000000-0000-0000-0000-000000000003',
    'New Grain Market, Sonipat',
    'Sonipat, Haryana',
    'Mustard',
    6200.00,
    '2026-03-01',
    '2026-04-30',
    false
),

(
    'c0000000-0000-0000-0000-000000000004',
    'New Grain Market, Hisar',
    'Hisar, Haryana',
    'Wheat',
    2585.00,
    '2026-04-01',
    '2026-05-15',
    false
),

(
    'c0000000-0000-0000-0000-000000000005',
    'Adampur Mandi',
    'Adampur, Hisar, Haryana',
    'Mustard',
    6200.00,
    '2026-03-01',
    '2026-04-30',
    false
),

(
    'c0000000-0000-0000-0000-000000000006',
    'New Grain Market, Ambala City',
    'Ambala, Haryana',
    'Wheat',
    2585.00,
    '2026-04-01',
    '2026-05-15',
    false
),

(
    'c0000000-0000-0000-0000-000000000007',
    'New Grain Market, Sirsa',
    'Sirsa, Haryana',
    'Mustard',
    6200.00,
    '2026-03-01',
    '2026-04-30',
    false
),

(
    'c0000000-0000-0000-0000-000000000008',
    'New Grain Market, Fatehabad',
    'Fatehabad, Haryana',
    'Wheat',
    2585.00,
    '2026-04-01',
    '2026-05-15',
    false
),

(
    'c0000000-0000-0000-0000-000000000009',
    'New Grain Market, Jind',
    'Jind, Haryana',
    'Gram',
    5875.00,
    '2026-03-01',
    '2026-04-30',
    false
),

(
    'c0000000-0000-0000-0000-000000000010',
    'New Grain Market, Kaithal',
    'Kaithal, Haryana',
    'Wheat',
    2585.00,
    '2026-04-01',
    '2026-05-15',
    false
),

-- ============================================================
-- PUNJAB
-- ============================================================

(
    'c0000000-0000-0000-0000-000000000011',
    'New Grain Market, Ludhiana',
    'Ludhiana, Punjab',
    'Wheat',
    2585.00,
    '2026-04-01',
    '2026-05-15',
    false
),

(
    'c0000000-0000-0000-0000-000000000012',
    'District Grain Market, Amritsar',
    'Amritsar, Punjab',
    'Paddy',
    2441.00,
    '2026-10-01',
    '2026-12-15',
    true
),

(
    'c0000000-0000-0000-0000-000000000013',
    'New Grain Market, Bathinda',
    'Bathinda, Punjab',
    'Bajra',
    2900.00,
    '2026-09-20',
    '2026-11-15',
    true
),

(
    'c0000000-0000-0000-0000-000000000014',
    'Anaj Mandi, Patiala',
    'Patiala, Punjab',
    'Wheat',
    2585.00,
    '2026-04-01',
    '2026-05-15',
    false
),

(
    'c0000000-0000-0000-0000-000000000015',
    'New Grain Market, Moga',
    'Moga, Punjab',
    'Paddy',
    2441.00,
    '2026-10-01',
    '2026-12-15',
    true
),

(
    'c0000000-0000-0000-0000-000000000016',
    'New Grain Market, Jalandhar',
    'Jalandhar, Punjab',
    'Wheat',
    2585.00,
    '2026-04-01',
    '2026-05-15',
    false
),

(
    'c0000000-0000-0000-0000-000000000017',
    'New Grain Market, Ferozepur',
    'Ferozepur, Punjab',
    'Paddy',
    2441.00,
    '2026-10-01',
    '2026-12-15',
    true
),

(
    'c0000000-0000-0000-0000-000000000018',
    'Ferozepur Cantonment APMC',
    'Ferozepur Cantt, Punjab',
    'Paddy',
    2441.00,
    '2026-10-01',
    '2026-12-15',
    true
),

(
    'c0000000-0000-0000-0000-000000000019',
    'Guru Har Sahai APMC',
    'Guruharsahai, Ferozepur, Punjab',
    'Paddy',
    2441.00,
    '2026-10-01',
    '2026-12-15',
    true
),

(
    'c0000000-0000-0000-0000-000000000020',
    'Talwandi Bhai APMC',
    'Talwandi Bhai, Ferozepur, Punjab',
    'Paddy',
    2441.00,
    '2026-10-01',
    '2026-12-15',
    true
),

-- ============================================================
-- UTTAR PRADESH
-- ============================================================

(
    'c0000000-0000-0000-0000-000000000021',
    'Krishi Utpadan Mandi Samiti, Meerut',
    'Meerut, Uttar Pradesh',
    'Wheat',
    2585.00,
    '2026-04-01',
    '2026-05-15',
    false
),

(
    'c0000000-0000-0000-0000-000000000022',
    'Krishi Utpadan Mandi Samiti, Muzaffarnagar',
    'Muzaffarnagar, Uttar Pradesh',
    'Maize',
    2410.00,
    '2026-09-01',
    '2026-11-30',
    true
),

(
    'c0000000-0000-0000-0000-000000000023',
    'Krishi Utpadan Mandi Samiti, Saharanpur',
    'Saharanpur, Uttar Pradesh',
    'Paddy',
    2441.00,
    '2026-10-01',
    '2026-12-15',
    true
),

(
    'c0000000-0000-0000-0000-000000000024',
    'Krishi Utpadan Mandi Samiti, Moradabad',
    'Moradabad, Uttar Pradesh',
    'Wheat',
    2585.00,
    '2026-04-01',
    '2026-05-15',
    false
),

(
    'c0000000-0000-0000-0000-000000000025',
    'Krishi Utpadan Mandi Samiti, Bareilly',
    'Bareilly, Uttar Pradesh',
    'Wheat',
    2585.00,
    '2026-04-01',
    '2026-05-15',
    false
),

(
    'c0000000-0000-0000-0000-000000000026',
    'Krishi Utpadan Mandi Samiti, Aligarh',
    'Aligarh, Uttar Pradesh',
    'Maize',
    2410.00,
    '2026-09-01',
    '2026-11-30',
    true
),

(
    'c0000000-0000-0000-0000-000000000027',
    'Krishi Utpadan Mandi Samiti, Agra',
    'Agra, Uttar Pradesh',
    'Wheat',
    2585.00,
    '2026-04-01',
    '2026-05-15',
    false
),

(
    'c0000000-0000-0000-0000-000000000028',
    'Krishi Utpadan Mandi Samiti, Lucknow',
    'Lucknow, Uttar Pradesh',
    'Paddy',
    2441.00,
    '2026-10-01',
    '2026-12-15',
    true
),

(
    'c0000000-0000-0000-0000-000000000029',
    'Krishi Utpadan Mandi Samiti, Kanpur',
    'Kanpur, Uttar Pradesh',
    'Maize',
    2410.00,
    '2026-09-01',
    '2026-11-30',
    true
),

(
    'c0000000-0000-0000-0000-000000000030',
    'Krishi Utpadan Mandi Samiti, Shahjahanpur',
    'Shahjahanpur, Uttar Pradesh',
    'Wheat',
    2585.00,
    '2026-04-01',
    '2026-05-15',
    false
),

-- ============================================================
-- RAJASTHAN
-- ============================================================

(
    'c0000000-0000-0000-0000-000000000031',
    'Anaj Mandi, Sri Ganganagar',
    'Sri Ganganagar, Rajasthan',
    'Wheat',
    2585.00,
    '2026-04-01',
    '2026-05-15',
    false
),

(
    'c0000000-0000-0000-0000-000000000032',
    'Krishi Upaj Mandi, Hanumangarh',
    'Hanumangarh, Rajasthan',
    'Wheat',
    2585.00,
    '2026-04-01',
    '2026-05-15',
    false
),

(
    'c0000000-0000-0000-0000-000000000033',
    'Krishi Upaj Mandi, Kota',
    'Kota, Rajasthan',
    'Mustard',
    6200.00,
    '2026-03-01',
    '2026-04-30',
    false
),

(
    'c0000000-0000-0000-0000-000000000034',
    'Krishi Upaj Mandi, Baran',
    'Baran, Rajasthan',
    'Mustard',
    6200.00,
    '2026-03-01',
    '2026-04-30',
    false
),

(
    'c0000000-0000-0000-0000-000000000035',
    'Anta APMC',
    'Anta, Baran, Rajasthan',
    'Wheat',
    2585.00,
    '2026-04-01',
    '2026-05-15',
    false
),

(
    'c0000000-0000-0000-0000-000000000036',
    'Atru APMC',
    'Atru, Baran, Rajasthan',
    'Mustard',
    6200.00,
    '2026-03-01',
    '2026-04-30',
    false
),

(
    'c0000000-0000-0000-0000-000000000037',
    'Chhabra APMC',
    'Chhabra, Baran, Rajasthan',
    'Mustard',
    6200.00,
    '2026-03-01',
    '2026-04-30',
    false
),

(
    'c0000000-0000-0000-0000-000000000038',
    'Dholpur APMC',
    'Dholpur, Rajasthan',
    'Mustard',
    6200.00,
    '2026-03-01',
    '2026-04-30',
    false
),

(
    'c0000000-0000-0000-0000-000000000039',
    'Hindoun APMC',
    'Hindoun, Karauli, Rajasthan',
    'Mustard',
    6200.00,
    '2026-03-01',
    '2026-04-30',
    false
),

(
    'c0000000-0000-0000-0000-000000000040',
    'Jaisalmer APMC',
    'Jaisalmer, Rajasthan',
    'Bajra',
    2900.00,
    '2026-09-01',
    '2026-11-30',
    true
)

ON CONFLICT (id) DO UPDATE SET
    name       = EXCLUDED.name,
    location   = EXCLUDED.location,
    crop_type  = EXCLUDED.crop_type,
    msp_rate   = EXCLUDED.msp_rate,
    open_date  = EXCLUDED.open_date,
    close_date = EXCLUDED.close_date,
    is_active  = EXCLUDED.is_active;

