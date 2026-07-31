// Dashboard initialization and management

document.addEventListener('DOMContentLoaded', function() {
    // Initialize dashboard components
    initDashboard();
    
    // Set up refresh interval (every 60 seconds)
    setInterval(refreshDashboardData, 60000);
    
    // Set up event listeners
    setupEventListeners();
});

// Initialize the dashboard
function initDashboard() {
    // Fetch initial data
    fetchAccountBalance();
    fetchLatestPrices();
    fetchActivePositions();
    fetchRecentTrades();
    fetchRecentSignals();
    
    // Initialize portfolio charts
    fetchPortfolioData();
}

// Refresh dashboard data
function refreshDashboardData() {
    fetchAccountBalance();
    fetchLatestPrices();
    fetchActivePositions();
    fetchRecentSignals();
}

// Setup event listeners for dashboard interactions
function setupEventListeners() {
    // Close position button clicks
    document.querySelectorAll('.close-position-btn').forEach(button => {
        button.addEventListener('click', function(e) {
            const positionId = this.getAttribute('data-position-id');
            closePosition(positionId);
        });
    });
    
    // Execute signal button clicks
    document.querySelectorAll('.execute-signal-btn').forEach(button => {
        button.addEventListener('click', function(e) {
            const signalId = this.getAttribute('data-signal-id');
            executeSignal(signalId);
        });
    });
    
    // Manual trade form submission
    const manualTradeForm = document.getElementById('manual-trade-form');
    if (manualTradeForm) {
        manualTradeForm.addEventListener('submit', function(e) {
            e.preventDefault();
            submitManualTrade();
        });
    }
}

// Fetch account balance data
function fetchAccountBalance() {
    fetch('/api/account-balance')
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch account balance');
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                updateAccountBalanceUI(data.data);
            } else {
                console.error('Error fetching account balance:', data.error);
                showErrorMessage('No trading accounts connected. Please add API credentials in Settings.');
            }
        })
        .catch(error => {
            console.error('Error fetching account balance:', error);
            showErrorMessage('Failed to load account balance data.');
        });
}

// Update the account balance UI elements
function updateAccountBalanceUI(balanceData) {
    const balanceContainer = document.getElementById('account-balance-container');
    if (!balanceContainer) return;
    
    let html = '';
    
    // Process each platform's balance
    for (const platform in balanceData) {
        const platformData = balanceData[platform];
        
        if (platform === 'binance') {
            html += `<div class="card mb-3">
                <div class="card-header">Binance Account</div>
                <div class="card-body">`;
            
            // Display balances for each asset
            if (platformData.balances) {
                html += `<table class="table table-sm table-dark">
                    <thead>
                        <tr>
                            <th>Asset</th>
                            <th>Free</th>
                            <th>Locked</th>
                            <th>Total</th>
                        </tr>
                    </thead>
                    <tbody>`;
                
                for (const asset in platformData.balances) {
                    const balance = platformData.balances[asset];
                    html += `<tr>
                        <td>${asset}</td>
                        <td>${balance.free.toFixed(8)}</td>
                        <td>${balance.locked.toFixed(8)}</td>
                        <td><strong>${balance.total.toFixed(8)}</strong></td>
                    </tr>`;
                }
                
                html += `</tbody></table>`;
            }
            
            html += `</div></div>`;
        }
        else if (platform === 'oanda') {
            html += `<div class="card mb-3">
                <div class="card-header">OANDA Account</div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-6">
                            <p><strong>Balance:</strong> ${platformData.balance.toFixed(2)} ${platformData.currency}</p>
                            <p><strong>NAV:</strong> ${platformData.net_asset_value.toFixed(2)} ${platformData.currency}</p>
                            <p><strong>Margin Available:</strong> ${platformData.margin_available.toFixed(2)} ${platformData.currency}</p>
                        </div>
                        <div class="col-md-6">
                            <p><strong>Margin Used:</strong> ${platformData.margin_used.toFixed(2)} ${platformData.currency}</p>
                            <p><strong>Unrealized P&L:</strong> ${platformData.unrealized_pl.toFixed(2)} ${platformData.currency}</p>
                            <p><strong>Open Positions:</strong> ${platformData.positions}</p>
                        </div>
                    </div>
                </div>
            </div>`;
        }
    }
    
    // If no balance data is available
    if (html === '') {
        html = `<div class="alert alert-warning">No account balance data available. Please configure your API keys in the settings.</div>`;
    }
    
    balanceContainer.innerHTML = html;
}

// Fetch latest market prices
function fetchLatestPrices() {
    fetch('/api/prices')
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch latest prices');
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                updateLatestPricesUI(data.data);
            } else {
                console.error('Error fetching latest prices:', data.error);
                showErrorMessage('No market data available. Please configure API credentials in Settings.');
            }
        })
        .catch(error => {
            console.error('Error fetching latest prices:', error);
            showErrorMessage('Failed to load latest price data.');
        });
}

// Update the latest prices UI
function updateLatestPricesUI(priceData) {
    const pricesContainer = document.getElementById('latest-prices-container');
    if (!pricesContainer) return;
    
    let html = '<div class="row">';
    
    // Create price cards
    let count = 0;
    for (const pair in priceData) {
        const price = priceData[pair];
        
        // Determine if cryptocurrency or forex
        const isCrypto = pair.includes('USDT') || pair.includes('BTC');
        const icon = isCrypto ? 
            '<i class="fas fa-coins me-2"></i>' : 
            '<i class="fas fa-money-bill-wave me-2"></i>';
        
        html += `<div class="col-md-3 col-sm-6 mb-3">
            <div class="card h-100">
                <div class="card-body text-center">
                    <h6>${icon}${pair}</h6>
                    <h4 class="price-current">${price.toFixed(isCrypto ? 6 : 4)}</h4>
                </div>
            </div>
        </div>`;
        
        count++;
        // Limit to 8 pairs on dashboard
        if (count >= 8) break;
    }
    
    html += '</div>';
    
    pricesContainer.innerHTML = html;
}

// Fetch active positions
function fetchActivePositions() {
    fetch('/api/positions')
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch active positions');
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                updateActivePositionsUI(data.data);
            } else {
                console.error('Error fetching active positions:', data.error);
                updateActivePositionsUI([]);
            }
        })
        .catch(error => {
            console.error('Error fetching active positions:', error);
            updateActivePositionsUI([]);
        });
}

// Update the active positions UI
function updateActivePositionsUI(positions) {
    const positionsContainer = document.getElementById('active-positions-container');
    if (!positionsContainer) return;
    
    if (positions.length === 0) {
        positionsContainer.innerHTML = '<div class="alert alert-info">No active positions at the moment.</div>';
        return;
    }
    
    let html = `<div class="table-responsive">
        <table class="table table-dark table-hover">
            <thead>
                <tr>
                    <th>Pair</th>
                    <th>Type</th>
                    <th>Amount</th>
                    <th>Entry</th>
                    <th>Current</th>
                    <th>P&L</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>`;
    
    positions.forEach(position => {
        const pnlClass = position.pnl > 0 ? 'text-success' : (position.pnl < 0 ? 'text-danger' : '');
        const rowClass = position.pnl > 0 ? 'position-profit' : (position.pnl < 0 ? 'position-loss' : '');
        
        html += `<tr class="${rowClass}">
            <td>${position.symbol}</td>
            <td>${position.side === 'buy' ? '<span class="badge bg-success">BUY</span>' : '<span class="badge bg-danger">SELL</span>'}</td>
            <td>${position.size ? parseFloat(position.size).toFixed(4) : 'N/A'}</td>
            <td>${position.entry_price ? parseFloat(position.entry_price).toFixed(6) : 'N/A'}</td>
            <td>${position.current_price ? position.current_price.toFixed(6) : 'N/A'}</td>
            <td class="${pnlClass}">${position.pnl ? position.pnl.toFixed(2) : '0.00'}</td>
            <td>
                <button class="btn btn-sm btn-outline-danger close-position-btn" data-position-id="${position.id}">
                    Close
                </button>
            </td>
        </tr>`;
    });
    
    html += `</tbody></table></div>`;
    positionsContainer.innerHTML = html;
    
    // Re-attach event listeners for close buttons
    document.querySelectorAll('.close-position-btn').forEach(button => {
        button.addEventListener('click', function() {
            const positionId = this.getAttribute('data-position-id');
            closePosition(positionId);
        });
    });
}

// Close a position
function closePosition(positionId) {
    if (!confirm('Are you sure you want to close this position?')) {
        return;
    }
    
    // Show loading state
    const button = document.querySelector(`.close-position-btn[data-position-id="${positionId}"]`);
    if (button) {
        button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Closing...';
        button.disabled = true;
    }
    
    fetch(`/api/positions/${positionId}/close`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to close position');
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                showSuccessMessage('Position closed successfully.');
                fetchActivePositions();  // Refresh positions
                fetchAccountBalance();   // Refresh account balance
                fetchRecentTrades();     // Refresh recent trades
            } else {
                showErrorMessage(data.error || 'Failed to close position.');
            }
        })
        .catch(error => {
            console.error('Error closing position:', error);
            showErrorMessage('Failed to close position. Please try again.');
            
            // Reset button state
            if (button) {
                button.innerHTML = 'Close';
                button.disabled = false;
            }
        });
}

// Fetch recent trades
function fetchRecentTrades() {
    fetch('/api/trades?limit=10')
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch recent trades');
            }
            return response.json();
        })
        .then(data => {
            updateRecentTradesUI(data);
        })
        .catch(error => {
            console.error('Error fetching recent trades:', error);
            showErrorMessage('Failed to load recent trades data.');
        });
}

// Update the recent trades UI
function updateRecentTradesUI(trades) {
    const tradesContainer = document.getElementById('recent-trades-container');
    if (!tradesContainer) return;
    
    if (trades.length === 0) {
        tradesContainer.innerHTML = '<div class="alert alert-info">No trade history available.</div>';
        return;
    }
    
    let html = `<div class="table-responsive">
        <table class="table table-dark table-sm">
            <thead>
                <tr>
                    <th>Time</th>
                    <th>Pair</th>
                    <th>Type</th>
                    <th>Price</th>
                    <th>Amount</th>
                    <th>P&L</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>`;
    
    trades.forEach(trade => {
        const date = new Date(trade.timestamp);
        const formattedDate = date.toLocaleString();
        const pnlClass = trade.pnl > 0 ? 'text-success' : (trade.pnl < 0 ? 'text-danger' : '');
        
        html += `<tr>
            <td>${formattedDate}</td>
            <td>${trade.trading_pair}</td>
            <td>${trade.order_type === 'BUY' ? '<span class="badge bg-success">BUY</span>' : '<span class="badge bg-danger">SELL</span>'}</td>
            <td>${trade.price.toFixed(6)}</td>
            <td>${trade.amount.toFixed(4)}</td>
            <td class="${pnlClass}">${trade.pnl ? trade.pnl.toFixed(2) : '-'}</td>
            <td><span class="badge bg-${getStatusBadgeColor(trade.status)}">${trade.status}</span></td>
        </tr>`;
    });
    
    html += `</tbody></table></div>`;
    tradesContainer.innerHTML = html;
}

// Get appropriate badge color for trade status
function getStatusBadgeColor(status) {
    switch (status.toLowerCase()) {
        case 'filled':
        case 'completed':
            return 'success';
        case 'pending':
            return 'warning';
        case 'canceled':
        case 'cancelled':
            return 'secondary';
        case 'rejected':
        case 'failed':
            return 'danger';
        default:
            return 'info';
    }
}

// Fetch recent signals
function fetchRecentSignals() {
    fetch('/api/signals?limit=10')
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch recent signals');
            }
            return response.json();
        })
        .then(data => {
            updateRecentSignalsUI(data);
        })
        .catch(error => {
            console.error('Error fetching recent signals:', error);
            showErrorMessage('Failed to load recent signals data.');
        });
}

// Update the recent signals UI
function updateRecentSignalsUI(signals) {
    const signalsContainer = document.getElementById('recent-signals-container');
    if (!signalsContainer) return;
    
    if (signals.length === 0) {
        signalsContainer.innerHTML = '<div class="alert alert-info">No recent signals available.</div>';
        return;
    }
    
    let html = `<div class="table-responsive">
        <table class="table table-dark table-sm">
            <thead>
                <tr>
                    <th>Time</th>
                    <th>Pair</th>
                    <th>Signal</th>
                    <th>Entry</th>
                    <th>Stop Loss</th>
                    <th>Take Profit</th>
                    <th>Confidence</th>
                    <th>Status</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>`;
    
    signals.forEach(signal => {
        const date = new Date(signal.timestamp);
        const formattedDate = date.toLocaleString();
        const signalClass = signal.signal_type === 'BUY' ? 'signal-buy' : 'signal-sell';
        const confidencePercent = signal.confidence ? (signal.confidence * 100).toFixed(0) + '%' : 'N/A';
        
        html += `<tr>
            <td>${formattedDate}</td>
            <td>${signal.trading_pair}</td>
            <td class="${signalClass}"><strong>${signal.signal_type}</strong></td>
            <td>${signal.entry_price.toFixed(6)}</td>
            <td>${signal.stop_loss.toFixed(6)}</td>
            <td>${signal.take_profit.toFixed(6)}</td>
            <td>${confidencePercent}</td>
            <td><span class="badge bg-${getSignalStatusBadgeColor(signal.status)}">${signal.status}</span></td>
            <td>`;
        
        if (signal.status === 'pending') {
            html += `<button class="btn btn-sm btn-primary execute-signal-btn" data-signal-id="${signal.id}">
                Execute
            </button>`;
        } else {
            html += `<button class="btn btn-sm btn-outline-secondary" disabled>
                ${signal.status}
            </button>`;
        }
        
        html += `</td></tr>`;
    });
    
    html += `</tbody></table></div>`;
    signalsContainer.innerHTML = html;
    
    // Re-attach event listeners for execute buttons
    document.querySelectorAll('.execute-signal-btn').forEach(button => {
        button.addEventListener('click', function() {
            const signalId = this.getAttribute('data-signal-id');
            executeSignal(signalId);
        });
    });
}

// Get appropriate badge color for signal status
function getSignalStatusBadgeColor(status) {
    switch (status.toLowerCase()) {
        case 'executed':
            return 'success';
        case 'pending':
            return 'warning';
        case 'canceled':
        case 'expired':
            return 'secondary';
        case 'failed':
            return 'danger';
        default:
            return 'info';
    }
}

// Execute a trade based on a signal
function executeSignal(signalId) {
    if (!confirm('Are you sure you want to execute this signal?')) {
        return;
    }
    
    // Show loading state
    const button = document.querySelector(`.execute-signal-btn[data-signal-id="${signalId}"]`);
    if (button) {
        button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Executing...';
        button.disabled = true;
    }
    
    fetch(`/api/signals/${signalId}/execute`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to execute signal');
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                showSuccessMessage('Signal executed successfully.');
                fetchRecentSignals();   // Refresh signals
                fetchActivePositions(); // Refresh positions
                fetchAccountBalance();  // Refresh account balance
            } else {
                showErrorMessage(data.error || 'Failed to execute signal.');
            }
        })
        .catch(error => {
            console.error('Error executing signal:', error);
            showErrorMessage('Failed to execute signal. Please try again.');
            
            // Reset button state
            if (button) {
                button.innerHTML = 'Execute';
                button.disabled = false;
            }
        });
}

// Submit a manual trade
function submitManualTrade() {
    const form = document.getElementById('manual-trade-form');
    if (!form) return;
    
    const formData = new FormData(form);
    const tradeData = {
        trading_pair: formData.get('trading_pair'),
        order_type: formData.get('order_type'),
        amount: parseFloat(formData.get('amount')),
        price: formData.get('market_order') ? null : parseFloat(formData.get('price')),
        stop_loss: parseFloat(formData.get('stop_loss')) || null,
        take_profit: parseFloat(formData.get('take_profit')) || null,
        platform: formData.get('platform')
    };
    
    // Show loading state
    const submitButton = form.querySelector('button[type="submit"]');
    const originalButtonText = submitButton.innerHTML;
    submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Executing...';
    submitButton.disabled = true;
    
    fetch('/api/execute-trade', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(tradeData)
    })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to execute trade');
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                showSuccessMessage('Trade executed successfully.');
                form.reset();
                fetchActivePositions(); // Refresh positions
                fetchAccountBalance();  // Refresh account balance
                fetchRecentTrades();    // Refresh recent trades
            } else {
                showErrorMessage(data.error || 'Failed to execute trade.');
            }
        })
        .catch(error => {
            console.error('Error executing trade:', error);
            showErrorMessage('Failed to execute trade. Please try again.');
        })
        .finally(() => {
            // Reset button state
            submitButton.innerHTML = originalButtonText;
            submitButton.disabled = false;
        });
}

// Fetch portfolio risk and allocation data
function fetchPortfolioData() {
    // Fetch portfolio risk metrics
    fetch('/api/portfolio-risk')
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch portfolio risk data');
            }
            return response.json();
        })
        .then(riskData => {
            updatePortfolioRiskUI(riskData);
        })
        .catch(error => {
            console.error('Error fetching portfolio risk data:', error);
        });
    
    // Fetch position exposure
    fetch('/api/position-exposure')
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch position exposure data');
            }
            return response.json();
        })
        .then(exposureData => {
            updatePortfolioAllocationUI(exposureData);
        })
        .catch(error => {
            console.error('Error fetching position exposure data:', error);
        });
}

// Update portfolio risk UI
function updatePortfolioRiskUI(riskData) {
    const riskContainer = document.getElementById('portfolio-risk-container');
    if (!riskContainer) return;
    
    let html = `<div class="row">
        <div class="col-md-6 col-lg-3 mb-3">
            <div class="card">
                <div class="card-body text-center">
                    <h6>Win Rate</h6>
                    <h4>${(riskData.win_rate * 100).toFixed(2)}%</h4>
                </div>
            </div>
        </div>
        <div class="col-md-6 col-lg-3 mb-3">
            <div class="card">
                <div class="card-body text-center">
                    <h6>Profit Factor</h6>
                    <h4>${isFinite(riskData.profit_factor) ? riskData.profit_factor.toFixed(2) : '∞'}</h4>
                </div>
            </div>
        </div>
        <div class="col-md-6 col-lg-3 mb-3">
            <div class="card">
                <div class="card-body text-center">
                    <h6>Exposure</h6>
                    <h4>${(riskData.exposure_ratio * 100).toFixed(2)}%</h4>
                </div>
            </div>
        </div>
        <div class="col-md-6 col-lg-3 mb-3">
            <div class="card">
                <div class="card-body text-center">
                    <h6>Max Drawdown</h6>
                    <h4>${riskData.max_drawdown.toFixed(2)}%</h4>
                </div>
            </div>
        </div>
    </div>`;
    
    riskContainer.innerHTML = html;
}

// Update portfolio allocation UI
function updatePortfolioAllocationUI(exposureData) {
    const allocationContainer = document.getElementById('portfolio-allocation-container');
    if (!allocationContainer) return;
    
    // Create container for charts
    allocationContainer.innerHTML = `
        <div class="row">
            <div class="col-md-6 mb-3">
                <div class="card h-100">
                    <div class="card-header">Asset Class Allocation</div>
                    <div class="card-body">
                        <canvas id="asset-class-chart"></canvas>
                    </div>
                </div>
            </div>
            <div class="col-md-6 mb-3">
                <div class="card h-100">
                    <div class="card-header">Position Allocation</div>
                    <div class="card-body">
                        <canvas id="position-allocation-chart"></canvas>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Create charts
    createAssetClassChart('asset-class-chart', exposureData);
    createPortfolioAllocationChart('position-allocation-chart', exposureData);
}

// Show success message
function showSuccessMessage(message) {
    const alertsContainer = document.getElementById('alerts-container');
    if (!alertsContainer) return;
    
    const alertElement = document.createElement('div');
    alertElement.className = 'alert alert-success alert-dismissible fade show';
    alertElement.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    alertsContainer.appendChild(alertElement);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        alertElement.classList.remove('show');
        setTimeout(() => alertElement.remove(), 500);
    }, 5000);
}

// Show error message
function showErrorMessage(message) {
    const alertsContainer = document.getElementById('alerts-container');
    if (!alertsContainer) return;
    
    const alertElement = document.createElement('div');
    alertElement.className = 'alert alert-danger alert-dismissible fade show';
    alertElement.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    alertsContainer.appendChild(alertElement);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        alertElement.classList.remove('show');
        setTimeout(() => alertElement.remove(), 500);
    }, 5000);
}
