// Firebase Configuration
import { initializeApp } from "firebase/app";

const firebaseConfig = {
  apiKey: "AIzaSyCbUWktW3fQBgDHeMFcLK6g7-4jQ4wzX7g",
  authDomain: "forex-trader-db449.firebaseapp.com",
  projectId: "forex-trader-db449",
  storageBucket: "forex-trader-db449.firebasestorage.app",
  messagingSenderId: "895738865438",
  appId: "1:895738865438:web:bfc64bea59f144c500cb0f"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

export default app;
