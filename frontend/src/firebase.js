import { initializeApp } from "firebase/app";
import { getFirestore } from "firebase/firestore";
import { getAnalytics } from "firebase/analytics";

const firebaseConfig = {
  apiKey: "AIzaSyByTNIHyVcGFtg6cuR27ezq2bCfQJDkqw8",
  authDomain: "cloud-project-74451.firebaseapp.com",
  projectId: "cloud-project-74451",
  storageBucket: "cloud-project-74451.firebasestorage.app",
  messagingSenderId: "245298990451",
  appId: "1:245298990451:web:6a8db998a9432aa8a34906",
  measurementId: "G-N4PHPWFEDK"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Analytics
const analytics = getAnalytics(app);

// Firestore database
export const db = getFirestore(app);

export default app;