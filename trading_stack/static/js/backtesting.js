// Backtesting functionality

document.addEventListener('DOMContentLoaded', function() {
    // Initialize backtesting interface
    initBacktesting();
    
    // Set up form submission handlers
    setupEventListeners();
});

// Initialize backtesting page
function initBacktesting() {
    // Fetch available strategies
    fetchStrategies();
    
    // Fetch trading pairs
    fetchTradingPairs();
    
    // Set up default dates
    setDefaultDates();
}

// Set up event listeners
function setupEventListeners() {
    // Backtest form submission
    const backtestForm = document.getElementById('backtest-form');
    if (backtestForm) {
        backtestForm.addEventListener('submit', function(e) {
            e.preventDefault();
            runBacktest();
        });
    }
    
    // Strategy change event
    const strategySelect = document.getElementById('strategy-select');
    if (strategySelect) {
        strategySelect.addEventListener('change', function() {
            fetchStrategyDetails(this.value);
        });
    }
}

// Set default dates (1 year ago to today)
function setDefaultDates() {
    const endDate = new Date();
    const startDate = new Date();
    startDate.setFullYear(startDate.getFullYear() - 1);
    
    const startDateInput = document.getElementById('start-date');
    const endDateInput = document.getElementById('end-date');
    
    if (startDateInput) {
        startDateInput.value = formatDateForInput(startDate);
    }
    
    if (endDateInput) {
        endDateInput.value = formatDateForInput(endDate);
    }
}

// Format date for input fields (YYYY-MM-DD)
function formatDateForInput(date) {
    const year = date.getFullYear();
    const month = (date.getMonth() + 1).toString().padStart(2, '0');
    const day = date.getDate().toString().padStart(2, '0');
    return `${year}-${month}-${day}`;
}

// Fetch available strategies
function fetchStrategies() {
    fetch('/api/strategies')
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch strategies');
            }
            return response.json();
        })
        .then(strategies => {
            updateStrategiesSelect(strategies);
            
            // If there are strategies, load the first one's details
            if (strategies.length > 0) {
                fetchStrategyDetails(strategies[0].id);
            }
        })
        .catch(error => {
            console.error('Error fetching strategies:', error);
            showBacktestError('Failed to load strategies. Please refresh the page and try again.');
        });
}

// Update the strategies select dropdown
function updateStrategiesSelect(strategies) {
    const strategySelect = document.getElementById('strategy-select');
    if (!strategySelect) return;
    
    // Clear existing options
    strategySelect.innerHTML = '';
    
    // Add strategies to select
    strategies.forEach(strategy => {
        const option = document.createElement('option');
        option.value = strategy.id;
        option.textContent = strategy.name;
        strategySelect.appendChild(option);
    });
    
    // If no strategies available
    if (strategies.length === 0) {
        const option = document.createElement('option');
        option.value = '';
        option.textContent = 'No strategies available';
        option.disabled = true;
        strategySelect.appendChild(option);
        strategySelect.disabled = true;
        
        // Show message about creating strategies
        const strategiesContainer = document.getElementById('strategy-details-container');
        if (strategiesContainer) {
            strategiesContainer.innerHTML = `
                <div class="alert alert-info">
                    You don't have any trading strategies yet. 
                    <a href="/strategy-editor" class="alert-link">Create a strategy</a> to start backtesting.
                </div>
            `;
        }
    }
}

// Fetch trading pairs
function fetchTradingPairs() {
    // Crypto pairs
    const cryptoPairs = [
        "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "ADA/USDT", 
        "XRP/USDT", "DOT/USDT", "DOGE/USDT", "AVAX/USDT", "MATIC/USDT"
    ];
    
    // Forex pairs
    const forexPairs = [
        "EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CAD", 
        "USD/CHF", "NZD/USD", "EUR/GBP", "EUR/JPY", "GBP/JPY"
    ];
    
    // Update the trading pair select
    updateTradingPairsSelect(cryptoPairs, forexPairs);
}

// Update the trading pairs select dropdown
function updateTradingPairsSelect(cryptoPairs, forexPairs) {
    const pairSelect = document.getElementById('trading-pair-select');
    if (!pairSelect) return;
    
    // Clear existing options
    pairSelect.innerHTML = '';
    
    // Add crypto pairs group
    const cryptoGroup = document.createElement('optgroup');
    cryptoGroup.label = 'Cryptocurrency';
    
    cryptoPairs.forEach(pair => {
        const option = document.createElement('option');
        option.value = pair;
        option.textContent = pair;
        cryptoGroup.appendChild(option);
    });
    
    pairSelect.appendChild(cryptoGroup);
    
    // Add forex pairs group
    const forexGroup = document.createElement('optgroup');
    forexGroup.label = 'Forex';
    
    forexPairs.forEach(pair => {
        const option = document.createElement('option');
        option.value = pair;
        option.textContent = pair;
        forexGroup.appendChild(option);
    });
    
    pairSelect.appendChild(forexGroup);
}

// Fetch strategy details
function fetchStrategyDetails(strategyId) {
    if (!strategyId) return;
    
    fetch(`/api/strategies/${strategyId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch strategy details');
            }
            return response.json();
        })
        .then(strategy => {
            updateStrategyDetails(strategy);
        })
        .catch(error => {
            console.error('Error fetching strategy details:', error);
            showBacktestError('Failed to load strategy details.');
        });
}

// Helper function to safely escape HTML content
function escapeHtml(text) {
    if (text == null) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Update the strategy details display
function updateStrategyDetails(strategy) {
    const detailsContainer = document.getElementById('strategy-details-container');
    if (!detailsContainer) return;
    
    // Create safe HTML with escaped user content
    let html = `
        <div class="card mb-3">
            <div class="card-header">Strategy Details</div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-6">
                        <p><strong>Name:</strong> ${escapeHtml(strategy.name)}</p>
                        <p><strong>Timeframe:</strong> ${escapeHtml(strategy.timeframe)}</p>
                        <p><strong>Risk per Trade:</strong> ${strategy.risk_per_trade_pct}%</p>
                        <p><strong>Stop Loss:</strong> ${strategy.stop_loss_pct}%</p>
                        <p><strong>Take Profit:</strong> ${strategy.take_profit_pct}%</p>
                    </div>
                    <div class="col-md-6">
                        <p><strong>Description:</strong> ${escapeHtml(strategy.description || 'No description provided')}</p>
                        <p><strong>Trading Pairs:</strong> ${escapeHtml(strategy.trading_pairs.join(', '))}</p>
                        <p><strong>ML Model:</strong> ${strategy.use_ml_model ? 'Yes' : 'No'}</p>
                        <p><strong>Status:</strong> ${strategy.is_active ? '<span class="badge bg-success">Active</span>' : '<span class="badge bg-secondary">Inactive</span>'}</p>
                    </div>
                </div>
                
                <div class="mt-3">
                    <h6>Indicators</h6>
                    <div class="row">
    `;
    
    // Add indicators
    const indicators = strategy.indicators_config || {};
    if (Object.keys(indicators).length > 0) {
        Object.entries(indicators).forEach(([indicator, params], index) => {
            html += `
                <div class="col-md-4 mb-2">
                    <div class="card">
                        <div class="card-body p-2">
                            <strong>${escapeHtml(indicator.toUpperCase())}</strong>
                            <ul class="mb-0 ps-3">
            `;
            
            Object.entries(params).forEach(([param, value]) => {
                html += `<li>${escapeHtml(param)}: ${escapeHtml(value)}</li>`;
            });
            
            html += `
                            </ul>
                        </div>
                    </div>
                </div>
            `;
        });
    } else {
        html += `
            <div class="col-12">
                <div class="alert alert-info mb-0">No indicators configured</div>
            </div>
        `;
    }
    
    html += `
                    </div>
                </div>
                
                <div class="mt-3">
                    <h6>Entry Conditions</h6>
                    <div class="row">
    `;
    
    // Add entry conditions
    const entryConditions = strategy.entry_conditions || [];
    if (entryConditions.length > 0) {
        entryConditions.forEach(condition => {
            const conditionClass = condition.signal_type === 'BUY' ? 'border-success' : 'border-danger';
            const signalBadge = condition.signal_type === 'BUY' ? 
                '<span class="badge bg-success">BUY</span>' : 
                '<span class="badge bg-danger">SELL</span>';
            
            html += `
                <div class="col-md-6 mb-2">
                    <div class="card ${conditionClass} border">
                        <div class="card-body p-2">
                            ${signalBadge} 
                            <strong>${escapeHtml(condition.indicator)}</strong> 
                            ${escapeHtml(condition.operator)} 
                            ${escapeHtml(condition.value)}
                        </div>
                    </div>
                </div>
            `;
        });
    } else {
        html += `
            <div class="col-12">
                <div class="alert alert-info mb-0">No entry conditions configured</div>
            </div>
        `;
    }
    
    html += `
                    </div>
                </div>
                
                <div class="mt-3">
                    <h6>Exit Conditions</h6>
                    <div class="row">
    `;
    
    // Add exit conditions
    const exitConditions = strategy.exit_conditions || [];
    if (exitConditions.length > 0) {
        exitConditions.forEach(condition => {
            html += `
                <div class="col-md-6 mb-2">
                    <div class="card">
                        <div class="card-body p-2">
                            <strong>${escapeHtml(condition.indicator)}</strong> 
                            ${escapeHtml(condition.operator)} 
                            ${escapeHtml(condition.value)}
                        </div>
                    </div>
                </div>
            `;
        });
    } else {
        html += `
            <div class="col-12">
                <div class="alert alert-info mb-0">No exit conditions configured (using stop loss/take profit only)</div>
            </div>
        `;
    }
    
    html += `
                    </div>
                </div>
            </div>
        </div>
    `;
    
    detailsContainer.innerHTML = html;
    
    // Update trading pair select with strategy's pairs if available
    if (strategy.trading_pairs && strategy.trading_pairs.length > 0) {
        const pairSelect = document.getElementById('trading-pair-select');
        if (pairSelect) {
            const firstAvailablePair = strategy.trading_pairs[0];
            if (Array.from(pairSelect.options).some(option => option.value === firstAvailablePair)) {
                pairSelect.value = firstAvailablePair;
            }
        }
    }
    
    // Update timeframe if available
    if (strategy.timeframe) {
        const timeframeSelect = document.getElementById('timeframe-select');
        if (timeframeSelect) {
            if (Array.from(timeframeSelect.options).some(option => option.value === strategy.timeframe)) {
                timeframeSelect.value = strategy.timeframe;
            }
        }
    }
}

// Run backtest
function runBacktest() {
    // Get form values
    const strategyId = document.getElementById('strategy-select').value;
    const tradingPair = document.getElementById('trading-pair-select').value;
    const timeframe = document.getElementById('timeframe-select').value;
    const startDate = document.getElementById('start-date').value;
    const endDate = document.getElementById('end-date').value;
    const initialBalance = parseFloat(document.getElementById('initial-balance').value);
    
    // Validate inputs
    if (!strategyId || !tradingPair || !timeframe || !startDate || !endDate || isNaN(initialBalance)) {
        showBacktestError('Please fill in all fields with valid values.');
        return;
    }
    
    // Show loading state
    const resultsContainer = document.getElementById('backtest-results-container');
    resultsContainer.innerHTML = `
        <div class="text-center my-5">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-2">Running backtest... This may take a minute.</p>
        </div>
    `;
    
    // Prepare request data
    const backtestData = {
        strategy_id: strategyId,
        trading_pair: tradingPair,
        start_date: new Date(startDate).toISOString(),
        end_date: new Date(endDate).toISOString(),
        initial_balance: initialBalance
    };
    
    // Run the backtest
    fetch('/api/backtests', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(backtestData)
    })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to run backtest');
            }
            return response.json();
        })
        .then(data => {
            if (data.success && data.backtest_id) {
                // Get backtest results
                getBacktestResults(data.backtest_id);
            } else {
                showBacktestError(data.error || 'Failed to run backtest.');
            }
        })
        .catch(error => {
            console.error('Error running backtest:', error);
            showBacktestError('Failed to run backtest. Please try again.');
        });
}

// Get backtest results
function getBacktestResults(backtestId) {
    fetch(`/api/backtests/${backtestId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to get backtest results');
            }
            return response.json();
        })
        .then(data => {
            displayBacktestResults(data);
        })
        .catch(error => {
            console.error('Error getting backtest results:', error);
            showBacktestError('Failed to get backtest results. Please try again.');
        });
}

// Display backtest results
function displayBacktestResults(results) {
    const resultsContainer = document.getElementById('backtest-results-container');
    if (!resultsContainer) return;
    
    // Clear container
    resultsContainer.innerHTML = '';
    
    // Basic results summary
    let html = `
        <div class="card mb-3">
            <div class="card-header">Backtest Results</div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-6">
                        <p><strong>Strategy:</strong> ${escapeHtml(results.strategy_name)}</p>
                        <p><strong>Trading Pair:</strong> ${escapeHtml(results.trading_pair)}</p>
                        <p><strong>Timeframe:</strong> ${escapeHtml(results.timeframe)}</p>
                        <p><strong>Period:</strong> ${escapeHtml(new Date(results.start_date).toLocaleDateString())} to ${escapeHtml(new Date(results.end_date).toLocaleDateString())}</p>
                    </div>
                    <div class="col-md-6">
                        <p><strong>Initial Balance:</strong> ${escapeHtml(results.initial_balance.toFixed(2))}</p>
                        <p><strong>Final Balance:</strong> ${escapeHtml(results.final_balance.toFixed(2))}</p>
                        <p><strong>Profit/Loss:</strong> <span class="${results.final_balance > results.initial_balance ? 'text-success' : 'text-danger'}">${escapeHtml((results.final_balance - results.initial_balance).toFixed(2))} (${escapeHtml(((results.final_balance / results.initial_balance - 1) * 100).toFixed(2))}%)</span></p>
                        <p><strong>Max Drawdown:</strong> ${escapeHtml(results.max_drawdown_pct.toFixed(2))}%</p>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="row">
            <div class="col-md-6">
                <div class="card mb-3">
                    <div class="card-header">
                        Trade Statistics
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-6">
                                <p><strong>Total Trades:</strong> ${escapeHtml(results.total_trades)}</p>
                                <p><strong>Winning Trades:</strong> ${escapeHtml(results.winning_trades)}</p>
                                <p><strong>Losing Trades:</strong> ${escapeHtml(results.losing_trades)}</p>
                                <p><strong>Win Rate:</strong> ${escapeHtml(((results.winning_trades / results.total_trades) * 100).toFixed(2))}%</p>
                            </div>
                            <div class="col-6">
                                <p><strong>Profit Factor:</strong> ${escapeHtml(results.profit_factor ? results.profit_factor.toFixed(2) : 'N/A')}</p>
                                <p><strong>Sharpe Ratio:</strong> ${escapeHtml(results.sharpe_ratio ? results.sharpe_ratio.toFixed(2) : 'N/A')}</p>
                                <p><strong>Avg. Win:</strong> ${escapeHtml(results.result_data.metrics.average_profit ? results.result_data.metrics.average_profit.toFixed(2) : 'N/A')}</p>
                                <p><strong>Avg. Loss:</strong> ${escapeHtml(results.result_data.metrics.average_loss ? results.result_data.metrics.average_loss.toFixed(2) : 'N/A')}</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="col-md-6">
                <div class="card mb-3">
                    <div class="card-header">
                        Performance Metrics
                    </div>
                    <div class="card-body">
                        <canvas id="performance-metrics-chart" height="200"></canvas>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="card mb-3">
            <div class="card-header">Equity Curve</div>
            <div class="card-body">
                <div style="height: 400px;">
                    <canvas id="equity-curve-chart"></canvas>
                </div>
            </div>
        </div>
        
        <div class="card mb-3">
            <div class="card-header">Trade List</div>
            <div class="card-body">
                <div class="table-responsive backtest-results">
                    <table class="table table-sm table-striped table-dark">
                        <thead>
                            <tr>
                                <th>Entry Time</th>
                                <th>Exit Time</th>
                                <th>Type</th>
                                <th>Entry Price</th>
                                <th>Exit Price</th>
                                <th>Size</th>
                                <th>P&L</th>
                                <th>Exit Reason</th>
                            </tr>
                        </thead>
                        <tbody>
    `;
    
    // Add trades
    const trades = results.result_data.trades || [];
    trades.forEach(trade => {
        const entryDate = escapeHtml(new Date(trade.entry_time).toLocaleString());
        const exitDate = escapeHtml(new Date(trade.exit_time).toLocaleString());
        const pnlClass = trade.pnl > 0 ? 'text-success' : (trade.pnl < 0 ? 'text-danger' : '');
        const pnlPercent = trade.pnl / trade.size * 100;
        
        html += `
            <tr>
                <td>${entryDate}</td>
                <td>${exitDate}</td>
                <td>${escapeHtml(trade.type) === 'BUY' ? '<span class="badge bg-success">BUY</span>' : '<span class="badge bg-danger">SELL</span>'}</td>
                <td>${escapeHtml(trade.entry_price.toFixed(6))}</td>
                <td>${escapeHtml(trade.exit_price.toFixed(6))}</td>
                <td>${escapeHtml(trade.size.toFixed(4))}</td>
                <td class="${pnlClass}">${escapeHtml(trade.pnl.toFixed(2))} (${escapeHtml(pnlPercent.toFixed(2))}%)</td>
                <td>${escapeHtml(trade.exit_reason)}</td>
            </tr>
        `;
    });
    
    html += `
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    `;
    
    // Safe assignment since all dynamic content is now escaped
    resultsContainer.innerHTML = html;
    
    // Create charts
    if (results.result_data) {
        // Create equity curve chart
        if (results.result_data.equity_curve && results.result_data.drawdown_curve) {
            createBacktestChart('equity-curve-chart', results.result_data);
        }
        
        // Create performance metrics chart
        if (results.result_data.metrics) {
            createPerformanceMetricsChart('performance-metrics-chart', results.result_data.metrics);
        }
    }
}

// Show backtest error message
function showBacktestError(message) {
    const resultsContainer = document.getElementById('backtest-results-container');
    if (!resultsContainer) return;
    
    resultsContainer.innerHTML = `
        <div class="alert alert-danger">
            <i class="fas fa-exclamation-triangle me-2"></i> ${escapeHtml(message)}
        </div>
    `;
}
