# E2E Test Report — Marketing Agent v2

**Date:** 2026-01-29
**Runner:** Playwright 1.58
**Browsers:** Chromium, Firefox, WebKit
**Total tests:** 60 (20 tests x 3 browsers)
**Result:** 60 passed, 0 failed

## Test Suites

### `e2e/onboarding.spec.ts` (4 tests)
| Test | Status |
|------|--------|
| Welcome screen loads with heading and domain input | PASS |
| Domain input accepts text | PASS |
| Submit triggers processing state | PASS |
| Error state shows retry option | PASS |

### `e2e/dashboard.spec.ts` (7 tests)
| Test | Status |
|------|--------|
| Dashboard loads with sidebar navigation | PASS |
| Sidebar shows all nav items: Chat, Campaigns, Assets, Brand | PASS |
| Can navigate between Chat, Campaigns, Assets, Brand views | PASS |
| Campaigns view shows empty state or campaign list | PASS |
| Chat input is visible and accepts text | PASS |
| Chat send button exists | PASS |
| Kata Lab button is visible in sidebar | PASS |

### `e2e/kata-lab.spec.ts` (4 tests)
| Test | Status |
|------|--------|
| Kata Lab page loads with header | PASS |
| Mode selector shows 3 modes | PASS |
| Can switch between modes | PASS |
| Back button returns to dashboard | PASS |

### `e2e/navigation.spec.ts` (5 tests)
| Test | Status |
|------|--------|
| App renders without crashing | PASS |
| Fresh load shows onboarding (no org in localStorage) | PASS |
| With org ID, shows dashboard | PASS |
| Can navigate from dashboard to Kata Lab and back | PASS |
| Logout returns to onboarding | PASS |

## Scripts

```bash
npm run test:e2e          # Run all tests headless
npm run test:e2e:ui       # Open interactive UI mode
npm run test:e2e:report   # View HTML report
```

## Notes

- Tests run against the Vite dev server (auto-started by Playwright).
- Backend (port 8000) is not required for UI-level tests; onboarding submit tests gracefully handle backend absence.
- Screenshots are captured on failure and stored in `test-results/`.
- HTML report is generated in `playwright-report/`.
