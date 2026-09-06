import { useNavigate } from "react-router-dom";
import "./HomePage.css";

export default function HomePage() {
  const navigate = useNavigate();

  return (
    <div className="home-page">
      {/* HERO */}
      <section className="home-hero">
        <div className="home-hero-text">
          <span className="home-brand">🌾 KisanSaarthi</span>
          <h1>Voice-first procurement, built for every farmer.</h1>
          <p>
            No app. No literacy barrier. Just a phone call — book a token, get
            real-time queue updates, and track your payment, all in your own
            language.
          </p>
          <button className="home-cta" onClick={() => navigate("/login")}>
            Login to Dashboard
          </button>
        </div>
        <div className="home-hero-image">
          <img src="/hero-hands.jpg" alt="Farmer planting a sapling" />
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section className="home-how">
        <h2>How it works</h2>
        <div className="home-how-grid">
          <div className="home-how-card">
            <span className="home-how-icon">📞</span>
            <h3>Call &amp; Book</h3>
            <p>
              Farmer calls in, the system identifies them and recommends a less
              congested centre or time slot — no forms, no typing.
            </p>
          </div>
          <div className="home-how-card">
            <span className="home-how-icon">📋</span>
            <h3>Real-Time Queue</h3>
            <p>
              Once checked in, farmers can call anytime for live, accurate
              wait-time updates — no more guessing or standing in line all day.
            </p>
          </div>
          <div className="home-how-card">
            <span className="home-how-icon">💰</span>
            <h3>Transparent Payment</h3>
            <p>
              Every step — from procurement to payment processing to completion
              — is tracked and visible, with instant status updates.
            </p>
          </div>
        </div>
      </section>

      {/* IMPACT */}
      <section className="home-impact">
        <h2>Built for everyone in the procurement chain</h2>
        <div className="home-impact-grid">
          <div>
            <h3>For Farmers</h3>
            <p>
              Removes the digital divide — a natural-language voice interface
              replaces complex apps, giving instant access to scheduling, wait
              times, and payment tracking.
            </p>
          </div>
          <div>
            <h3>For Procurement Centres</h3>
            <p>
              A real-time dashboard eliminates administrative overhead and
              prevents bottlenecks with predictive slot allocation.
            </p>
          </div>
          <div>
            <h3>For Administrators</h3>
            <p>
              Centralized, cross-centre analytics for full visibility into
              procurement velocity, capacity, and settlement cycles.
            </p>
          </div>
        </div>
      </section>

      <section className="home-footer-cta">
        <h2>Ready to get started?</h2>
        <button className="home-cta" onClick={() => navigate("/login")}>
          Login
        </button>
      </section>
    </div>
  );
}
