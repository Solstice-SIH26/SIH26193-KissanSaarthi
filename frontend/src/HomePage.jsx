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

        <div className="hero-body">
          <div className="hero-content">
            <h1>
              One phone call.
              <br />
              Zero barriers.
            </h1>
            <p>
              A voice-first procurement platform that replaces apps, forms, and
              long queues with a simple phone call — in the farmer's own
              language.
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

          <div className="hero-flow">
            <h4>Two ways to book</h4>
            <div className="hero-flow-step">
              <span className="hero-flow-badge">1</span>
              <div>
                <strong>Call in</strong>
                <p>No app needed — speak in your own language</p>
              </div>
            </div>
            <div className="hero-flow-connector" />
            <div className="hero-flow-step">
              <span className="hero-flow-badge">2</span>
              <div>
                <strong>Or book on the dashboard</strong>
                <p>Log in and reserve a slot yourself</p>
              </div>
            </div>
            <div className="hero-flow-connector" />
            <div className="hero-flow-step">
              <span className="hero-flow-badge">3</span>
              <div>
                <strong>Get confirmed instantly</strong>
                <p>Via SMS and voice, either way</p>
              </div>
            </div>
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
          <span className="stat-number">2</span>
          <span className="stat-label">Ways to book — call or dashboard</span>
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
        <p className="home-how-sub">
          Book by phone if that's easier for you — or log in and book directly
          on the dashboard if you prefer. Either way, the process is the same.
        </p>
        <div className="home-how-grid">
          <div className="home-how-card">
            <span className="how-step">01</span>
            <h3>Book — By Call or Dashboard</h3>
            <p>
              Call in and the system identifies you instantly, or log in and
              pick a slot yourself. Either way, you get matched to a less
              congested centre or time slot.
            </p>
          </div>
          <div className="home-how-card">
            <span className="how-step">02</span>
            <h3>Real-Time Queue</h3>
            <p>
              Once checked in, check your queue position anytime — by phone or
              on the dashboard. No more standing around guessing.
            </p>
          </div>
          <div className="home-how-card">
            <span className="how-step">03</span>
            <h3>Transparent Payment</h3>
            <p>
              Every step — procurement, processing, completion — is tracked and
              visible, with instant status the moment it changes.
            </p>
          </div>
        </div>
      </section>

      {/* MISSION / SPLIT SECTION */}
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
            <li>✓ Multilingual voice interface, zero typing required</li>
            <li>✓ Smart slot-matching helps prevent overcrowded centres</li>
            <li>✓ Instant SMS and voice confirmations at every step</li>
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
              scheduling, live wait times, and payment tracking, by voice or on
              the dashboard.
            </p>
          </div>
          <div className="impact-card">
            <h3>Procurement Centres</h3>
            <p>
              A real-time dashboard eliminates administrative overhead and helps
              prevent bottlenecks through smarter slot allocation.
            </p>
          </div>
          <div className="impact-card">
            <h3>Administrators</h3>
            <p>
              A single view across every centre — track procurement volume,
              capacity, and payment cycles in one place.
            </p>
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="home-footer">
        <p className="home-footer-line">
          KisanSaarthi is built to make procurement simple, transparent, and
          accessible — for every farmer, regardless of literacy or access to a
          smartphone.
        </p>
        <div className="home-footer-bottom">
          <span>🌾 KisanSaarthi</span>
          <span>Smart India Hackathon 2026 · PS26032</span>
          <span>Built by Team Solstice</span>
        </div>
      </footer>
    </div>
  );
}
