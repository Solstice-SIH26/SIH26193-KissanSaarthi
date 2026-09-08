
import { useState, useEffect, useCallback } from "react";
import "./FarmerDashboard.css";

import { requestToken, getToken } from "../../services/tokenService.js";
import { getCenters } from "../../services/scheduleService.js";
import { getCropPrices } from "../../services/priceService.js";
import { supabase } from "../../supabaseClient";

/**
 * Map backend status to a human-readable label.
 */
const STATUS_LABELS = {
  pending: "Pending Approval",
  waiting: "Waiting",
  called: "Called",
  completed: "Completed",
  rejected: "Rejected",
  cancelled: "Cancelled",
};

function displayStatus(backendStatus) {
  return STATUS_LABELS[backendStatus] || backendStatus || "Unknown";
}

/**
 * Determine if a center is currently open.
 */
function isCenterOpen(openDate, closeDate) {
  if (!openDate || !closeDate) return false;

  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const open = new Date(openDate + "T00:00:00");
  const close = new Date(closeDate + "T23:59:59");

  return today >= open && today <= close;
}

/**
 * Format number as Indian Rupee.
 */
function formatPrice(amount) {
  return `₹${amount.toLocaleString("en-IN")}`;
}

/**
 * DISPLAY-ONLY helper: maps a backend status to a step index
 * for the visual progress tracker. Does not affect any logic.
 */
const STEP_ORDER = ["pending", "waiting", "called", "completed"];

function getStepIndex(status) {
  const index = STEP_ORDER.indexOf(status);
  return index === -1 ? -1 : index;
}

/**
 * Status badge.
 */
function StatusBadge({ status }) {
  const safeStatus = status || "Unknown";
  const modifier = safeStatus.toLowerCase().replace(/\s+/g, "-");

  return (
    <span
      className={`farmer-dash__status-badge farmer-dash__status-badge--${modifier}`}
      role="status"
    >
      <span className="farmer-dash__status-dot" aria-hidden="true" />
      {safeStatus}
    </span>
  );
}

/**
 * DISPLAY-ONLY: visual progress stepper for the token lifecycle.
 * Purely presentational — reads token.status, renders nothing
 * that other code depends on.
 */
function TokenProgress({ status }) {
  const isStopped = status === "rejected" || status === "cancelled";
  const currentStep = getStepIndex(status);

  const steps = [
    { key: "pending", label: "Requested" },
    { key: "waiting", label: "Approved" },
    { key: "called", label: "Called" },
    { key: "completed", label: "Completed" },
  ];

  if (isStopped) {
    return (
      <div className="farmer-dash__progress farmer-dash__progress--stopped">
        <span className="farmer-dash__progress-stopped-icon">✕</span>
        <span>
          {status === "rejected"
            ? "This request was rejected."
            : "This request was cancelled."}
        </span>
      </div>
    );
  }

  return (
    <div className="farmer-dash__progress">
      {steps.map((step, i) => (
        <div key={step.key} className="farmer-dash__progress-step">
          <div
            className={`farmer-dash__progress-dot ${
              i <= currentStep ? "farmer-dash__progress-dot--done" : ""
            } ${i === currentStep ? "farmer-dash__progress-dot--current" : ""}`}
          >
            {i < currentStep ? "✓" : i + 1}
          </div>

          <span
            className={`farmer-dash__progress-label ${
              i <= currentStep ? "farmer-dash__progress-label--done" : ""
            }`}
          >
            {step.label}
          </span>

          {i < steps.length - 1 && (
            <div
              className={`farmer-dash__progress-line ${
                i < currentStep ? "farmer-dash__progress-line--done" : ""
              }`}
            />
          )}
        </div>
      ))}
    </div>
  );
}

function FarmerDashboard() {
  /* ─────────────────────────────────────────────
     TOKEN / PROCUREMENT REQUEST STATE
  ───────────────────────────────────────────── */

  const [token, setToken] = useState(() => {
    const savedTokenId = localStorage.getItem("farmerTokenId");
    return savedTokenId ? { id: savedTokenId } : null;
  });

  const [tokenLoading, setTokenLoading] = useState(false);
  const [tokenError, setTokenError] = useState(null);
  const [isRefreshingToken, setIsRefreshingToken] = useState(false);

  /* ─────────────────────────────────────────────
     AUTHENTICATED FARMER STATE
  ───────────────────────────────────────────── */

  const [farmerId, setFarmerId] = useState(null);

  /* ─────────────────────────────────────────────
     CENTER STATE
  ───────────────────────────────────────────── */

  const [centers, setCenters] = useState([]);
  const [centersLoading, setCentersLoading] = useState(true);
  const [centersError, setCentersError] = useState(null);
  const [selectedCenterId, setSelectedCenterId] = useState("");

  /* ─────────────────────────────────────────────
     NEW PROCUREMENT REQUEST FIELDS
  ───────────────────────────────────────────── */

  const [requestedDate, setRequestedDate] = useState("");
  const [quantityKg, setQuantityKg] = useState("");

  /* ─────────────────────────────────────────────
     CROP PRICES
  ───────────────────────────────────────────── */

  const [prices, setPrices] = useState([]);
  const [pricesLoading, setPricesLoading] = useState(true);

  /* Selected center object */

  const selectedCenter =
    centers.find((c) => c.id === selectedCenterId) || null;

  /* ─────────────────────────────────────────────
     LOAD CURRENT AUTHENTICATED FARMER
  ───────────────────────────────────────────── */

  useEffect(() => {
    let cancelled = false;

    async function loadCurrentUser() {
      const { data, error } = await supabase.auth.getUser();

      if (cancelled) return;

      if (!error && data?.user) {
        setFarmerId(data.user.id);
      }
    }

    loadCurrentUser();

    return () => {
      cancelled = true;
    };
  }, []);

  /* ─────────────────────────────────────────────
     LOAD CENTERS
  ───────────────────────────────────────────── */

  useEffect(() => {
    let cancelled = false;

    async function loadCenters() {
      try {
        const data = await getCenters();

        if (cancelled) return;

        if (data && data.length > 0) {
          setCenters(data);
          setSelectedCenterId(data[0].id);
        } else {
          setCenters([]);
        }
      } catch {
        if (cancelled) return;

        setCentersError("Unable to load procurement centers.");
      } finally {
        if (!cancelled) {
          setCentersLoading(false);
        }
      }
    }

    loadCenters();

    return () => {
      cancelled = true;
    };
  }, []);

  /* ─────────────────────────────────────────────
     LOAD CROP PRICES
  ───────────────────────────────────────────── */

  useEffect(() => {
    let cancelled = false;

    async function loadPrices() {
      try {
        const data = await getCropPrices();

        if (cancelled) return;

        setPrices(data && data.length > 0 ? data : []);
      } catch {
        if (cancelled) return;

        setPrices([]);
      } finally {
        if (!cancelled) {
          setPricesLoading(false);
        }
      }
    }

    loadPrices();

    return () => {
      cancelled = true;
    };
  }, []);

  /* ─────────────────────────────────────────────
     REQUEST PROCUREMENT
  ───────────────────────────────────────────── */

  const handleRequestToken = useCallback(async () => {
    if (!farmerId || !selectedCenterId || !requestedDate || !quantityKg) {
      setTokenError("Please select a center, date, and quantity.");
      return;
    }

    const quantity = Number(quantityKg);

    if (!Number.isFinite(quantity) || quantity <= 0) {
      setTokenError("Quantity must be greater than 0 kg.");
      return;
    }

    setTokenLoading(true);
    setTokenError(null);

    try {
      const newToken = await requestToken(
        farmerId,
        selectedCenterId,
        requestedDate,
        selectedCenter?.crop_type,
        quantity
      );

      localStorage.setItem("farmerTokenId", newToken.id);

      setToken({
        id: newToken.id,
        tokenNumber: newToken.token_number,
        status: newToken.status,
        centerId: newToken.center_id,
        requestedDate: newToken.requested_date,
        cropType: newToken.crop_type,
        quantityKg: newToken.quantity_kg,
        timeSlot: newToken.time_slot,
      });

      setRequestedDate("");
      setQuantityKg("");
    } catch (err) {
      console.error("REQUEST TOKEN ERROR:", err);

      setTokenError(
        err.body?.detail ||
          (err.status
            ? `Request failed (${err.status}). Please try again.`
            : "Unable to reach the server. Please try again later.")
      );
    } finally {
      setTokenLoading(false);
    }
  }, [
    farmerId,
    selectedCenterId,
    requestedDate,
    quantityKg,
    selectedCenter,
  ]);

  /* ─────────────────────────────────────────────
     REFRESH TOKEN / REQUEST STATUS
  ───────────────────────────────────────────── */

  const handleRefreshToken = useCallback(async () => {
    if (!token) return;

    setIsRefreshingToken(true);
    setTokenError(null);

    try {
      const refreshedToken = await getToken(token.id);

      setToken({
        id: refreshedToken.id,
        tokenNumber: refreshedToken.token_number,
        status: refreshedToken.status,
        centerId: refreshedToken.center_id,
        requestedDate: refreshedToken.requested_date,
        cropType: refreshedToken.crop_type,
        quantityKg: refreshedToken.quantity_kg,
        timeSlot: refreshedToken.time_slot,
      });
    } catch (err) {
      setTokenError(
        err.status
          ? `Refresh failed (${err.status}). Please try again.`
          : "Unable to reach the server. Please try again later."
      );
    } finally {
      setIsRefreshingToken(false);
    }
  }, [token]);

  /* ─────────────────────────────────────────────
     RESTORE SAVED REQUEST ON PAGE LOAD
  ───────────────────────────────────────────── */

  useEffect(() => {
    const savedTokenId = localStorage.getItem("farmerTokenId");

    if (!savedTokenId) return;

    let cancelled = false;

    async function loadSavedToken() {
      try {
        const savedToken = await getToken(savedTokenId);

        if (cancelled) return;

        setToken({
          id: savedToken.id,
          tokenNumber: savedToken.token_number,
          status: savedToken.status,
          centerId: savedToken.center_id,
          requestedDate: savedToken.requested_date,
          cropType: savedToken.crop_type,
          quantityKg: savedToken.quantity_kg,
          timeSlot: savedToken.time_slot,
        });
      } catch {
        if (cancelled) return;

        localStorage.removeItem("farmerTokenId");

        setToken(null);
      }
    }

    loadSavedToken();

    return () => {
      cancelled = true;
    };
  }, []);

  /* ─────────────────────────────────────────────
     AUTO REFRESH EVERY 10 SECONDS
  ───────────────────────────────────────────── */

  useEffect(() => {
    if (!token) return;

    const intervalId = setInterval(() => {
      handleRefreshToken();
    }, 10000);

    return () => {
      clearInterval(intervalId);
    };
  }, [token, handleRefreshToken]);

  /* ─────────────────────────────────────────────
     CENTER NAME HELPER
  ───────────────────────────────────────────── */

  function centerName(centerId) {
    const center = centers.find((x) => x.id === centerId);

    return center ? center.name : "—";
  }

  /* ═════════════════════════════════════════════
     UI
  ═════════════════════════════════════════════ */

  return (
    <div className="farmer-dash">
      {/* HEADER */}

      <header className="farmer-dash__header">
        <span className="farmer-dash__header-icon" aria-hidden="true">
          🌾
        </span>

        <div>
          <h1 className="farmer-dash__title">Farmer Dashboard</h1>

          <p className="farmer-dash__subtitle">
            View your procurement request, schedule, and current crop prices.
          </p>
        </div>
      </header>

      {/* ═══════════════════════════════════════
          SECTION 1 — MY TOKEN / REQUEST
      ═══════════════════════════════════════ */}

      <section
        className="farmer-dash__section"
        aria-labelledby="token-heading"
      >
        <h2 id="token-heading" className="farmer-dash__section-title">
          <span aria-hidden="true">🎫</span> My Procurement Request
        </h2>

        <div className="farmer-dash__card farmer-dash__token-card">
          {token ? (
            <>
              <div className="farmer-dash__token-header">
                <span className="farmer-dash__token-number">
                  {token.tokenNumber
                    ? `#${token.tokenNumber}`
                    : "Token Pending"}
                </span>

                <StatusBadge status={displayStatus(token.status)} />
              </div>

              <TokenProgress status={token.status} />

              <dl className="farmer-dash__token-details">
                <div className="farmer-dash__detail-row">
                  <dt>Procurement Center</dt>
                  <dd>{centerName(token.centerId)}</dd>
                </div>

                <div className="farmer-dash__detail-row">
                  <dt>Crop</dt>
                  <dd>{token.cropType || "—"}</dd>
                </div>

                <div className="farmer-dash__detail-row">
                  <dt>Requested Date</dt>
                  <dd>{token.requestedDate || "—"}</dd>
                </div>

                <div className="farmer-dash__detail-row">
                  <dt>Quantity</dt>
                  <dd>
                    {token.quantityKg ? `${token.quantityKg} kg` : "—"}
                  </dd>
                </div>

                {token.timeSlot && (
                  <div className="farmer-dash__detail-row">
                    <dt>Time Slot</dt>
                    <dd>{token.timeSlot}</dd>
                  </div>
                )}
              </dl>

              <button
                type="button"
                className="farmer-dash__btn farmer-dash__btn--secondary"
                onClick={handleRefreshToken}
                disabled={isRefreshingToken}
                style={{ marginTop: "1rem" }}
              >
                {isRefreshingToken ? "Refreshing…" : "↻ Refresh Status"}
              </button>
            </>
          ) : (
            <div className="farmer-dash__empty-state farmer-dash__empty-state--card">
              <span className="farmer-dash__empty-icon" aria-hidden="true">
                📋
              </span>

              <p>
                No active procurement request.
                <br />
                Select a center, date, and quantity below to get started.
              </p>
            </div>
          )}

          {tokenError && (
            <p className="farmer-dash__error-msg" role="alert">
              ⚠ {tokenError}
            </p>
          )}

          {/* CENTER SELECTOR */}

          {centersLoading ? (
            <p className="farmer-dash__loading-msg">Loading centers…</p>
          ) : centersError ? (
            <p className="farmer-dash__error-msg" role="alert">
              ⚠ {centersError}
            </p>
          ) : centers.length > 0 ? (
            <div className="farmer-dash__center-select-row">
              <label
                htmlFor="center-select"
                className="farmer-dash__center-select-label"
              >
                Center
              </label>

              <select
                id="center-select"
                className="farmer-dash__center-select"
                value={selectedCenterId}
                onChange={(e) => setSelectedCenterId(e.target.value)}
              >
                {centers.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} — {c.crop_type}
                  </option>
                ))}
              </select>
            </div>
          ) : (
            <p className="farmer-dash__empty-state">
              No procurement centers available.
            </p>
          )}

          {/* REQUEST DATE */}

          <div className="farmer-dash__center-select-row">
            <label
              htmlFor="requested-date"
              className="farmer-dash__center-select-label"
            >
              Requested Date
            </label>

            <input
              id="requested-date"
              type="date"
              className="farmer-dash__center-select"
              value={requestedDate}
              onChange={(e) => setRequestedDate(e.target.value)}
              min={new Date().toISOString().split("T")[0]}
            />
          </div>

          {/* QUANTITY */}

          <div className="farmer-dash__center-select-row">
            <label
              htmlFor="quantity-kg"
              className="farmer-dash__center-select-label"
            >
              Quantity (kg)
            </label>

            <input
              id="quantity-kg"
              type="number"
              className="farmer-dash__center-select"
              value={quantityKg}
              onChange={(e) => setQuantityKg(e.target.value)}
              min="1"
              step="1"
              placeholder="Enter quantity"
            />
          </div>

          <button
            type="button"
            className="farmer-dash__btn farmer-dash__btn--primary"
            onClick={handleRequestToken}
            disabled={
              tokenLoading ||
              !farmerId ||
              !selectedCenterId ||
              !requestedDate ||
              !quantityKg
            }
          >
            {tokenLoading
              ? "Submitting Request…"
              : "Submit Procurement Request"}
          </button>
        </div>
      </section>

      {/* ═══════════════════════════════════════
          BOTTOM GRID
      ═══════════════════════════════════════ */}

      <div className="farmer-dash__grid">
        <section
          className="farmer-dash__section"
          aria-labelledby="schedule-heading"
        >
          <h2 id="schedule-heading" className="farmer-dash__section-title">
            <span aria-hidden="true">📅</span> Procurement Schedule
          </h2>

          <div className="farmer-dash__card">
            {centersLoading ? (
              <p className="farmer-dash__loading-msg">
                Loading schedule…
              </p>
            ) : selectedCenter ? (
              <dl className="farmer-dash__schedule-details">
                <div className="farmer-dash__detail-row">
                  <dt>Center</dt>
                  <dd>{selectedCenter.name}</dd>
                </div>

                <div className="farmer-dash__detail-row">
                  <dt>Location</dt>
                  <dd>{selectedCenter.location}</dd>
                </div>

                <div className="farmer-dash__detail-row">
                  <dt>Crop</dt>
                  <dd>{selectedCenter.crop_type}</dd>
                </div>

                <div className="farmer-dash__detail-row">
                  <dt>Opens</dt>
                  <dd>{selectedCenter.open_date || "—"}</dd>
                </div>

                <div className="farmer-dash__detail-row">
                  <dt>Closes</dt>
                  <dd>{selectedCenter.close_date || "—"}</dd>
                </div>

                <div className="farmer-dash__detail-row">
                  <dt>Status</dt>

                  <dd>
                    <StatusBadge
                      status={
                        isCenterOpen(
                          selectedCenter.open_date,
                          selectedCenter.close_date
                        )
                          ? "Open"
                          : "Closed"
                      }
                    />
                  </dd>
                </div>
              </dl>
            ) : (
              <p className="farmer-dash__empty-state">
                No centers available at this time.
              </p>
            )}
          </div>
        </section>

        <section
          className="farmer-dash__section"
          aria-labelledby="prices-heading"
        >
          <h2 id="prices-heading" className="farmer-dash__section-title">
            <span aria-hidden="true">💰</span> Crop Prices / MSP
          </h2>

          <div className="farmer-dash__card">
            {pricesLoading ? (
              <p className="farmer-dash__loading-msg">
                Loading prices…
              </p>
            ) : prices.length > 0 ? (
              <table className="farmer-dash__price-table">
                <thead>
                  <tr>
                    <th scope="col">Crop</th>
                    <th scope="col">MSP Rate</th>
                  </tr>
                </thead>

                <tbody>
                  {prices.map((item) => (
                    <tr key={item.crop}>
                      <td>{item.crop}</td>

                      <td className="farmer-dash__price-value">
                        {formatPrice(item.mspRate)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="farmer-dash__empty-state">
                No price data available.
              </p>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

export default FarmerDashboard;
