// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/utils/Counters.sol";

contract PlayerNFT is ERC721 {
    using Counters for Counters.Counter;
    Counters.Counter private _tokenIds;

    struct Player {
        string name;
        uint256 level;
    }

    mapping(uint256 => Player) public players;

    constructor() ERC721("PlayerNFT", "PNFT") {}

    function mintPlayer(string memory name) public {
        _tokenIds.increment();
        uint256 newId = _tokenIds.current();
        _safeMint(msg.sender, newId);
        players[newId] = Player(name, 1);
    }

    function levelUp(uint256 tokenId) public {
        require(ownerOf(tokenId) == msg.sender, "Not owner");
        players[tokenId].level += 1;
    }

    function getPlayer(uint256 tokenId) public view returns (string memory, uint256) {
        Player memory p = players[tokenId];
        return (p.name, p.level);
    }
}
