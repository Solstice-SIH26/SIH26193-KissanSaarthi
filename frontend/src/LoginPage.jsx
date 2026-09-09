import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { supabase } from './supabaseClient'
import './LoginPage.css'

export default function LoginPage() {
  const [loginMethod, setLoginMethod] = useState('email') // 'email' or 'phone'
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleLogin = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    await supabase.auth.signOut()


    let loginEmail = email

    if (loginMethod === 'phone') {
      let normalizedPhone = phone.replace(/\s+/g, '')
      // Ensure it starts with +91
      if (!normalizedPhone.startsWith('+91')) {
        // strip any leading 0 or +, then prepend +91
        normalizedPhone = normalizedPhone.replace(/^(\+?91|0)/, '')
        normalizedPhone = `+91${normalizedPhone}`
      }

      const { data: matchedProfile, error: lookupError } = await supabase
        .from('profiles')
        .select('id, phone')
        .eq('phone', normalizedPhone)
        .single()

      if (lookupError || !matchedProfile) {
        setError('Phone number not found')
        setLoading(false)
        return
      }

      loginEmail = `${normalizedPhone}@farmerapp.local`
    }

    const { data, error } = await supabase.auth.signInWithPassword({
      email: loginEmail,
      password,
    })

    setLoading(false)

    if (error) {
      setError(error.message)
      return
    }

    const { data: profile, error: profileError } = await supabase
      .from('profiles')
      .select('role')
      .eq('id', data.user.id)
      .single()

    if (profileError || !profile) {
      setError('Could not determine user role')
      return
    }

    if (profile.role === 'farmer') navigate('/farmer')
    else if (profile.role === 'procurement') navigate('/staff')
    else if (profile.role === 'admin') navigate('/admin')
  }

  return (
    <div className="login-page">

      {/* LEFT SIDE - FARMER IMAGE */}
      <div className="login-image">
        <img
          src="/farmer.jpg"
          alt="Farmer working in a field"
        />

        <div className="image-overlay">
          <h1>KisanSaarthi</h1>
          <p>
            Simple, smarter procurement<br />
            for every farmer.
          </p>
        </div>
      </div>

      {/* RIGHT SIDE - LOGIN */}
      <div className="login-panel">

        <div className="login-card">

          <div className="brand">
            <span className="brand-icon">🌾</span>
            <div>
              <h2>KisanSaarthi</h2>
              <p>Smart Agricultural Procurement</p>
            </div>
          </div>

          <h1>Welcome back</h1>

          <p className="subtitle">
            Login to access your procurement dashboard
          </p>

          {/* EMAIL / PHONE SWITCH */}
          <div className="login-method">
            <button
              type="button"
              className={loginMethod === 'email' ? 'active' : ''}
              onClick={() => {
                setLoginMethod('email')
                setError('')
              }}
            >
              Email
            </button>

            <button
              type="button"
              className={loginMethod === 'phone' ? 'active' : ''}
              onClick={() => {
                setLoginMethod('phone')
                setError('')
              }}
            >
              Phone
            </button>
          </div>

          <form onSubmit={handleLogin}>

            {loginMethod === 'email' ? (
              <>
                <label>Email address</label>

                <input
                  type="email"
                  placeholder="farmer@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </>
            ) : (
              <>
                <label>Phone number</label>

                <input
                  type="tel"
                  placeholder="+91 9876543210"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  required
                />
              </>
            )}

            <label>Password</label>

            <input
              type="password"
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />

            {error && (
              <div className="login-error">
                {error}
              </div>
            )}

            <button
              className="login-button"
              type="submit"
              disabled={loading}
            >
              {loading ? 'Logging in...' : 'Log In'}
            </button>

          </form>

          <p className="login-note">
            Farmers can login using email or phone.
            <br />
            Staff and administrators use email login.
          </p>

        </div>
      </div>
    </div>
  )
}