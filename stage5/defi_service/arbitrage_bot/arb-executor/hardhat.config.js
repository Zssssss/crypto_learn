require("@nomicfoundation/hardhat-toolbox");
require("dotenv").config();

module.exports = {
  solidity: "0.8.19",
  networks: {
    arbitrum: {
      url: process.env.ARB_RPC || "https://arb1.arbitrum.io/rpc",
      accounts: [process.env.PRIVATE_KEY].filter(Boolean),
    },
  },
};
