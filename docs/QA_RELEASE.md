# Quality and release checklist — PharmaVision AI

## Project status

**Version 0.3.0 — technical MVP / design stabilization.** The system is not a certified GPP solution, has no validated clinical AI, and must not be used with real patient records before security, privacy, pharmaceutical and legal reviews.

## Architecture and compatibility

- Backend: Python standard library `http.server` serving localhost by default.
- Data: SQLite tenant boundaries with user accounts and session/CSRF protections. Existing schema intentionally unchanged in this release.
- UI: no SPA framework, no Node runtime, no JavaScript CDN dependencies. Bundle CSS with `python tools/build_assets.py`.
- Icon set: inline outline SVG via `static/icons.js`; text fallback remains when JavaScript is unavailable.
- Fonts: native Arial / Segoe UI / Roboto / Noto Sans fallback. No remote web fonts required.
- Deploy: `deploy.ps1` verifies integration tests and CSS bundle, backs up SQLite using SQLite backup API, updates application files and attempts rollback when an update fails.

## Local checks

```sh
python tools/build_assets.py --check
python -m py_compile server.py test_app.py tools/build_assets.py
python -m unittest -v test_app.py
node --check static/workspace.js
node --check static/mobile.js
node --check static/icons.js
```

The `node --check` commands are optional local syntax checks when Node.js exists; Node.js is not required to run PharmaVision.

## Browser acceptance checklist

| Area | Acceptance criterion |
| --- | --- |
| Vietnamese display | No separated diacritics: Dược sĩ, Quản lý, Ngưỡng, Trường, Năng lực nền tảng |
| Landing page | No clipped CTA or feature cards on 320/360/390/430/768/1280/1440 px |
| Registration / login | Clear field validation, login via app credentials; no HTTP Basic Auth |
| Dashboard | Current tenant-only stats, alerts, sales chart, export |
| Navigation | Sidebar/mobile dock switch without old API response overwriting new screen; browser back works |
| Inventory | Search supports `duoc` matching `dược`, shows batches/expiry correctly |
| Point of sale | Live search, accurate stock checks, preserve cart form state, no duplicate checkout on double tap |
| Modal | Escape closes, focus remains inside open dialog, focus returns to prior button |
| Customer data | Consent gate required for health info; no data leaked between tenants |
| Offline font fallback | No remote font requests, native system fonts render Vietnamese |
| Mobile interactions | Safe area, 44px targets, barcode camera gracefully degrades without BarcodeDetector |
| Backend | No externally bound Python listener, HTTPS provided by Caddy |
| Deploy | Stops/restarts only PharmoraBackend, backups SQLite, rollback on failure |

## Known boundaries / roadmap

- The demand forecast is a simple 30-day sales baseline, not a trained predictive AI model.
- Copilot uses inventory matching/rules, not verified drug-drug interaction knowledge.
- BarcodeDetector browser support varies; manual code input is the fallback.
- OCR requires Tesseract on the server; it never approves a medicine for sale automatically.
- `http.server` + SQLite MVP is not approved for real clinical/financial records or multi-server scaling.
- Usability/accessibility need hands-on iOS Safari/Android Chrome testing, including VoiceOver/TalkBack.
- Before production, establish independent security assessment, threat modeling, backups/restore drills, privacy impact assessment and applicable pharmacy regulatory review.
