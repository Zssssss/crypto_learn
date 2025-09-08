import { useState } from "react";
import {
  WagmiConfig,
  createConfig,
  configureChains,
  useAccount,
  useConnect,
  useDisconnect,
  useContractWrite,
} from "wagmi";
import { sepolia } from "wagmi/chains";
import { publicProvider } from "wagmi/providers/public";
import { InjectedConnector } from "wagmi/connectors/injected";

const { chains, publicClient, webSocketPublicClient } = configureChains(
  [sepolia],
  [publicProvider()]
);

const config = createConfig({
  autoConnect: true,
  connectors: [new InjectedConnector({ chains })],
  publicClient,
  webSocketPublicClient,
});

// 部署后替换为你的合约地址
const contractAddress = "YOUR_DEPLOYED_CONTRACT_ADDRESS";
const abi = [
  {
    inputs: [{ internalType: "string", name: "name", type: "string" }],
    name: "mintPlayer",
    outputs: [],
    stateMutability: "nonpayable",
    type: "function",
  },
];

function NFTGame() {
  const { address, isConnected } = useAccount();
  const { connect } = useConnect({ connector: new InjectedConnector() });
  const { disconnect } = useDisconnect();
  const [name, setName] = useState("");

  const { write } = useContractWrite({
    address: contractAddress,
    abi,
    functionName: "mintPlayer",
  });

  return (
    <div style={{ padding: "20px" }}>
      {!isConnected ? (
        <button onClick={() => connect()}>Connect Wallet</button>
      ) : (
        <div>
          <p>Connected as: {address}</p>
          <button onClick={() => disconnect()}>Disconnect</button>
          <div>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Enter player name"
            />
            <button onClick={() => write({ args: [name] })}>
              Mint Player NFT
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function App() {
  return (
    <WagmiConfig config={config}>
      <NFTGame />
    </WagmiConfig>
  );
}
