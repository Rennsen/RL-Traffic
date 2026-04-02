"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export default function AuthPage() {
  const [login, setLogin] = useState({ email: "", password: "" });
  const [register, setRegister] = useState({ name: "", email: "", password: "" });
  const [message, setMessage] = useState("");

  async function handleLogin(event: React.FormEvent) {
    event.preventDefault();
    setMessage("");
    try {
      const response = await fetch(`${API_BASE}/api/auth/login_local`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(login),
        credentials: "include",
      });
      if (response.ok) {
        window.location.href = "/";
        return;
      }
      const text = await response.text();
      setMessage(text || "Login failed.");
    } catch (error) {
      setMessage(
        `Unable to reach the backend at ${API_BASE}. Make sure the API server is running.`,
      );
    }
  }

  async function handleRegister(event: React.FormEvent) {
    event.preventDefault();
    setMessage("");
    try {
      const response = await fetch(`${API_BASE}/api/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(register),
        credentials: "include",
      });
      if (response.ok) {
        window.location.href = "/";
        return;
      }
      const text = await response.text();
      setMessage(text || "Signup failed.");
    } catch (error) {
      setMessage(
        `Unable to reach the backend at ${API_BASE}. Make sure the API server is running.`,
      );
    }
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <section className="panel p-6 enter">
        <p className="eyebrow">Access</p>
        <h2 className="text-2xl font-semibold">Sign In or Create an Account</h2>
        <p className="mt-2 text-sm text-muted">
          Use local credentials or sign in with Google OAuth.
        </p>
      </section>

      {message ? (
        <div className="rounded-lg border border-danger/30 bg-danger/10 p-3 text-sm text-danger">
          {message}
        </div>
      ) : null}

      <section className="grid gap-6 lg:grid-cols-2">
        <form className="panel p-6 space-y-3" onSubmit={handleLogin}>
          <h3 className="text-lg font-semibold">Local Sign In</h3>
          <Input
            placeholder="Email"
            value={login.email}
            onChange={(event) => setLogin((current) => ({ ...current, email: event.target.value }))}
          />
          <Input
            placeholder="Password"
            type="password"
            value={login.password}
            onChange={(event) => setLogin((current) => ({ ...current, password: event.target.value }))}
          />
          <Button type="submit">Sign In</Button>
        </form>

        <form className="panel p-6 space-y-3" onSubmit={handleRegister}>
          <h3 className="text-lg font-semibold">Create Account</h3>
          <Input
            placeholder="Name"
            value={register.name}
            onChange={(event) => setRegister((current) => ({ ...current, name: event.target.value }))}
          />
          <Input
            placeholder="Email"
            value={register.email}
            onChange={(event) => setRegister((current) => ({ ...current, email: event.target.value }))}
          />
          <Input
            placeholder="Password"
            type="password"
            value={register.password}
            onChange={(event) => setRegister((current) => ({ ...current, password: event.target.value }))}
          />
          <Button variant="outline" type="submit">
            Sign Up
          </Button>
        </form>
      </section>

      <section className="panel p-6">
        <h3 className="text-lg font-semibold">Google OAuth</h3>
        <p className="text-sm text-muted mt-2">If configured, you can sign in with Google.</p>
        <a
          className="mt-4 inline-flex rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white"
          href={`${API_BASE}/api/auth/login`}
        >
          Sign in with Google
        </a>
      </section>
    </div>
  );
}
