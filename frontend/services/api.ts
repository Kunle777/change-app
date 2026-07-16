import axios from "axios";

const API_BASE_URL = "http://172.21.240.1:8000";

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});
