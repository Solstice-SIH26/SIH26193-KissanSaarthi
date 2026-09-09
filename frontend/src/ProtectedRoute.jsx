import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { supabase } from "./supabaseClient";

export default function ProtectedRoute({ children, allowedRole }) {
  const [session, setSession] = useState(null);
  const [role, setRole] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkUser = async () => {
      // Get logged-in user
      const { data: sessionData } = await supabase.auth.getSession();

      if (!sessionData.session) {
        setLoading(false);
        return;
      }

      setSession(sessionData.session);

      // Get user's role
      const { data: profile, error } = await supabase
        .from("profiles")
        .select("role")
        .eq("id", sessionData.session.user.id)
        .single();

      if (!error && profile) {
        setRole(profile.role);
      }

      setLoading(false);
    };

    checkUser();
  }, []);

  if (loading) {
    return <p>Loading...</p>;
  }

  // Not logged in
  if (!session) {
    return <Navigate to="/login" replace />;
  }

  // Logged in but wrong role
  if (allowedRole && role !== allowedRole) {
    if (role === "farmer") {
      return <Navigate to="/farmer" replace />;
    }

    if (role === "procurement") {
      return <Navigate to="/staff" replace />;
    }

    if (role === "admin") {
      return <Navigate to="/admin" replace />;
    }

    return <Navigate to="/login" replace />;
  }

  return children;
}
