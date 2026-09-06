import { useNavigate } from "react-router-dom";
import "./HomePage.css";

export default function HomePage() {
  const navigate = useNavigate();

  return (
    <div className="home-page">
      {/* FULL-BLEED HERO */}
      <section className="hero-full">
        <div className="hero-overlay" />
        <nav className="hero-nav">
          <span className="hero-brand">🌾 KisanSaarthi</span>
          <button className="nav-login" onClick={() => navigate("/login")}>
            Login
          </button>
        </nav>
        <div className="hero-content">
          <span className="hero-tag">Smart India Hackathon 2026 · PS26032</span>
          <h1>
            One phone call.
            <br />
            Zero barriers.
          </h1>
          <p>
            A voice-first procurement platform that replaces apps, forms, and
            long queues with a simple phone call — in the farmer's own language.
          </p>
          <div className="hero-buttons">
            <button
              className="hero-cta-primary"
              onClick={() => navigate("/login")}
            >
              Enter Dashboard →
            </button>
          </div>
        </div>
        <div className="hero-scroll-cue">↓ Scroll</div>
      </section>

      {/* STATS STRIP */}
      <section className="stats-strip">
        <div className="stat">
          <span className="stat-number">0</span>
          <span className="stat-label">Apps to install</span>
        </div>
        <div className="stat">
          <span className="stat-number">1</span>
          <span className="stat-label">Phone call to book</span>
        </div>
        <div className="stat">
          <span className="stat-number">Live</span>
          <span className="stat-label">Queue &amp; payment tracking</span>
        </div>
        <div className="stat">
          <span className="stat-number">24/7</span>
          <span className="stat-label">Voice access, any dialect</span>
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section className="home-how">
        <span className="section-eyebrow">The Flow</span>
        <h2>From call to cash, fully tracked</h2>
        <div className="home-how-grid">
          <div className="home-how-card">
            <span className="how-step">01</span>
            <h3>Call &amp; Book</h3>
            <p>
              Farmer calls in — the system identifies them instantly and
              recommends a less congested centre or time slot.
            </p>
          </div>
          <div className="home-how-card">
            <span className="how-step">02</span>
            <h3>Real-Time Queue</h3>
            <p>
              Once checked in, farmers call anytime for live, accurate wait-time
              updates. No more standing around guessing.
            </p>
          </div>
          <div className="home-how-card">
            <span className="how-step">03</span>
            <h3>Transparent Payment</h3>
            <p>
              Every step — procurement, processing, completion — tracked and
              visible, with instant status the moment it changes.
            </p>
          </div>
        </div>
      </section>

      {/* MISSION / SPLIT SECTION WITH SECOND IMAGE */}
      <section className="mission-split">
        <div className="mission-image">
          <img src="/hero-hands.jpg" alt="Farmer planting a sapling" />
        </div>
        <div className="mission-text">
          <span className="section-eyebrow">Why it matters</span>
          <h2>Built for the farmer who's never opened an app.</h2>
          <p>
            No literacy requirement. No smartphone requirement. Just a call, in
            a language they already speak — because digital inclusion shouldn't
            require a learning curve.
          </p>
          <ul className="mission-list">
            <li>✓ Multilingual voice interface, zero typing</li>
            <li>✓ Predictive slot-routing prevents overcrowding</li>
            <li>✓ Instant SMS + voice confirmations</li>
          </ul>
        </div>
      </section>

      {/* IMPACT */}
      <section className="home-impact">
        <span className="section-eyebrow">Impact</span>
        <h2>One platform, every stakeholder</h2>
        <div className="home-impact-grid">
          <div className="impact-card">
            <h3>Farmers</h3>
            <p>
              Removes the digital divide entirely — instant access to
              scheduling, live wait times, and payment tracking, by voice.
            </p>
          </div>
          <div className="impact-card">
            <h3>Procurement Centres</h3>
            <p>
              A real-time dashboard eliminates administrative overhead and
              prevents bottlenecks through predictive slot allocation.
            </p>
          </div>
          <div className="impact-card">
            <h3>Administrators</h3>
            <p>
              Centralized, cross-centre analytics for full visibility into
              procurement velocity, capacity, and settlement cycles.
            </p>
          </div>
        </div>
      </section>

      {/* FOOTER CTA */}
      <section className="home-footer-cta">
        <h2>See it in action.</h2>
        <button className="hero-cta-primary" onClick={() => navigate("/login")}>
          Enter Dashboard →
        </button>
      </section>
    </div>
  );
}
