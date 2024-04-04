// SPDX-License-Identifier: MIT
pragma solidity ^0.8.23;

contract ICO {

    address public immutable i_owner;
    uint public constant TOTAL_COIN_COUNT= 1e6;
    uint public constant USD_TO_COIN = 1e3;
    uint public s_totalCoinsBoughtCurrently;
    uint public s_totalCoinsBoughtGenerally;
    uint public s_totalCoinsSoldGenerally;

    mapping(address => uint) public equityCoin;
    mapping(address => uint) public equityUsd;

    constructor() {
        i_owner = msg.sender;
    }

    modifier canBuyCoin(uint usdInvested) {
        require(usdInvested * USD_TO_COIN + s_totalCoinsBoughtCurrently <= TOTAL_COIN_COUNT,
        "There are not enough coin to buy");
        _;
    }

    function buyCoins(uint usdInvested) 
    external
    canBuyCoin(usdInvested) {
        uint coinsBought = usdInvested * USD_TO_COIN;
        equityCoin[msg.sender] += coinsBought;
        equityUsd[msg.sender] = equityCoin[msg.sender] / USD_TO_COIN;
        s_totalCoinsBoughtCurrently += coinsBought;
        s_totalCoinsBoughtGenerally += coinsBought;
    }

    function sellCoins(uint usdGained) external {
        uint coinsSold = usdGained * USD_TO_COIN;
        equityCoin[msg.sender] -= usdGained * USD_TO_COIN;
        equityUsd[msg.sender] = equityCoin[msg.sender] / USD_TO_COIN;
        s_totalCoinsBoughtCurrently -= coinsSold;
        s_totalCoinsSoldGenerally += coinsSold;
    }

}
