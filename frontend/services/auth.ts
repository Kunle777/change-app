import { api } from "./api";

export async function register(
  email: string,
  password: string,
  phone?: string,
) {
  const response = await api.post("api/auth/register", {
    email,
    password,
    phone,
  });
  return response.data;
}

export async function login(email: string, password: string) {
  const response = await api.post("api/auth/login", { email, password });
  return response.data;
}

export async function getProfile(token: string) {
  const response = await api.get("/api/auth/profile", {
    headers: { Authorization: `Bearer ${token}` },
  });
  return response.data;
}
