import React, { useState } from "react";
import { ethers } from "ethers";

const App = () => {
  const [connected, setConnected] = useState(false);

  async function connectWallet() {
    if (!window.ethereum) {
      alert("Please install MetaMask");
      return;
    }
    await window.ethereum.request({ method: "eth_requestAccounts" });
    setConnected(true);
  }

  return (
    <div style={{ padding: 20 }}>
      <h1>Simple DeFi DApp</h1>
      {!connected ? (
        <button onClick={connectWallet}>Connect Wallet</button>
      ) : (
        <p>Wallet Connected ✅</p>
      )}
    </div>
  );
};

export default App;
