import axios from 'axios';

const api = axios.create({
  baseURL: `http://${window.location.hostname}:8000`,
  withCredentials: true,
});

export default api;