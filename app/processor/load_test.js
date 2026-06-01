import http from 'k6/http';
import { sleep } from 'k6';

const BASE_URL = 'http://localhost:8888';

export const options = {
  vus: 50,
  duration: '999m',
};

export default function () {
  http.post(`${BASE_URL}/send`);
  sleep(0.05);
}