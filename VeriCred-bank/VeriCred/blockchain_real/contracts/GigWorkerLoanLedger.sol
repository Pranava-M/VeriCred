// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title GigWorkerLoanLedger
 * @notice On-chain verification ledger for gig-worker loan decisions.
 *
 * Design notes for the report/viva:
 *  - Only the Merkle root of the underlying ride dataset is stored here,
 *    never the raw CSV — matches the "don't store raw data on-chain" rule.
 *  - Scores are stored as uint256 scaled by 100 (e.g. 93.85 -> 9385),
 *    since Solidity has no native floating point type.
 *  - Authentication does NOT need a separate on-chain signature check:
 *    every transaction sent to this contract is already signed by the
 *    caller's private key (that's how MetaMask/any wallet works) and the
 *    Polygon network itself verifies that before the transaction is even
 *    mined. The onlyOracle modifier below checks msg.sender, which is
 *    already cryptographically authenticated by the network — this IS
 *    the on-chain digital signature mechanism, not a workaround for one.
 *  - A second, independent signature layer (RSA, off-chain) exists in
 *    oracle_crypto.py for the simulated/offline demo mode. Both are
 *    legitimate; they authenticate at different layers.
 */
contract GigWorkerLoanLedger {

    address public owner;
    address public oracle;

    struct DecisionRecord {
        uint256 workerId;
        string applicationId;
        string applicantName;
        uint256 aiScoreScaled;     // e.g. 9385 = 93.85
        uint256 cibilScore;
        uint256 riskMeterScaled;   // e.g. 8660 = 86.60
        string riskBand;
        uint256 requestedAmountInr;
        bytes32 merkleRoot;        // fingerprint of the off-chain ride dataset
        string action;             // "FORWARDED_TO_MANAGER" | "DECLINED_BY_OFFICER"
        string reviewedBy;
        uint256 timestamp;
    }

    // Input shape mirrors DecisionRecord minus `timestamp` (set on-chain).
    // Packed into one struct parameter — passing 11 separate arguments to
    // one function hits Solidity's "stack too deep" compiler limit.
    struct DecisionInput {
        uint256 workerId;
        string applicationId;
        string applicantName;
        uint256 aiScoreScaled;
        uint256 cibilScore;
        uint256 riskMeterScaled;
        string riskBand;
        uint256 requestedAmountInr;
        bytes32 merkleRoot;
        string action;
        string reviewedBy;
    }

    // worker ID -> full history of decisions (append-only)
    mapping(uint256 => DecisionRecord[]) private workerHistory;

    // flat list of every worker ID that has at least one record, for enumeration
    uint256[] private allWorkerIds;
    mapping(uint256 => bool) private workerIdSeen;

    uint256 public totalRecords;

    event DecisionRecorded(
        uint256 indexed workerId,
        string applicationId,
        uint256 aiScoreScaled,
        uint256 riskMeterScaled,
        string action,
        bytes32 merkleRoot,
        uint256 timestamp
    );

    event OracleUpdated(address indexed oldOracle, address indexed newOracle);

    modifier onlyOwner() {
        require(msg.sender == owner, "Not contract owner");
        _;
    }

    modifier onlyOracle() {
        require(msg.sender == oracle, "Caller is not the authorized oracle");
        _;
    }

    constructor(address _oracle) {
        owner = msg.sender;
        oracle = _oracle;
    }

    /**
     * @notice Records one loan decision on-chain. Called by the oracle
     * process (a Flask backend using web3.py, signing with the oracle's
     * private key) after an officer forwards or declines an application.
     */
    function recordDecision(DecisionInput calldata input) external onlyOracle returns (uint256 recordIndex) {
        DecisionRecord memory record = DecisionRecord({
            workerId: input.workerId,
            applicationId: input.applicationId,
            applicantName: input.applicantName,
            aiScoreScaled: input.aiScoreScaled,
            cibilScore: input.cibilScore,
            riskMeterScaled: input.riskMeterScaled,
            riskBand: input.riskBand,
            requestedAmountInr: input.requestedAmountInr,
            merkleRoot: input.merkleRoot,
            action: input.action,
            reviewedBy: input.reviewedBy,
            timestamp: block.timestamp
        });

        workerHistory[input.workerId].push(record);
        recordIndex = workerHistory[input.workerId].length - 1;

        if (!workerIdSeen[input.workerId]) {
            workerIdSeen[input.workerId] = true;
            allWorkerIds.push(input.workerId);
        }

        totalRecords += 1;

        emit DecisionRecorded(
            input.workerId, input.applicationId, input.aiScoreScaled, input.riskMeterScaled,
            input.action, input.merkleRoot, block.timestamp
        );
    }

    /// @notice Returns the full decision history for one worker.
    function getWorkerHistory(uint256 workerId) external view returns (DecisionRecord[] memory) {
        return workerHistory[workerId];
    }

    /// @notice Returns just the most recent decision for one worker.
    function getLatestDecision(uint256 workerId) external view returns (DecisionRecord memory) {
        DecisionRecord[] storage history = workerHistory[workerId];
        require(history.length > 0, "No records for this worker");
        return history[history.length - 1];
    }

    /// @notice Checks whether a freshly-recomputed Merkle root matches what's on-chain
    ///         for a worker's latest decision — the on-chain half of the tamper check.
    function verifyLatestMerkleRoot(uint256 workerId, bytes32 rootToCheck) external view returns (bool) {
        DecisionRecord[] storage history = workerHistory[workerId];
        if (history.length == 0) return false;
        return history[history.length - 1].merkleRoot == rootToCheck;
    }

    function getAllWorkerIds() external view returns (uint256[] memory) {
        return allWorkerIds;
    }

    /// @notice Lets the contract owner rotate the oracle's authorized address
    ///         (e.g. if the oracle's private key needs to be replaced).
    function updateOracle(address newOracle) external onlyOwner {
        require(newOracle != address(0), "Invalid address");
        address old = oracle;
        oracle = newOracle;
        emit OracleUpdated(old, newOracle);
    }
}
