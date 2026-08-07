// Chart initialization and management

let priceChart = null;
let indicatorCharts = {};

// Initialize the main price chart
function initPriceChart(containerId) {
    const ctx = document.getElementById(containerId).getContext('2d');
    
    priceChart = new Chart(ctx, {
        type: 'candlestick',
        data: {
            datasets: [{
                label: 'Price',
                data: []
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'day',
                        displayFormats: {
                            day: 'MMM d'
                        }
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: 'rgba(255, 255, 255, 0.7)'
                    }
                },
                y: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: 'rgba(255, 255, 255, 0.7)'
                    }
                }
            },
            plugins: {
                legend: {
                    labels: {
                        color: 'rgba(255, 255, 255, 0.7)'
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            }
        }
    });
    
    return priceChart;
}

// Initialize an indicator chart
function initIndicatorChart(containerId, indicatorName) {
    const ctx = document.getElementById(containerId).getContext('2d');
    
    const chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: indicatorName,
                data: [],
                borderColor: getIndicatorColor(indicatorName),
                tension: 0.1,
                fill: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'day'
                    },
                    grid: {
                        display: false
                    },
                    ticks: {
                        color: 'rgba(255, 255, 255, 0.7)'
                    }
                },
                y: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: 'rgba(255, 255, 255, 0.7)'
                    }
                }
            },
            plugins: {
                legend: {
                    labels: {
                        color: 'rgba(255, 255, 255, 0.7)'
                    }
                }
            }
        }
    });
    
    indicatorCharts[indicatorName] = chart;
    return chart;
}

// Update the price chart with new data
function updatePriceChart(data) {
    if (!priceChart) return;
    
    const chartData = data.map(item => ({
        x: new Date(item.timestamp),
        o: item.open,
        h: item.high,
        l: item.low,
        c: item.close
    }));
    
    priceChart.data.datasets[0].data = chartData;
    priceChart.update();
}

// Update an indicator chart with new data
function updateIndicatorChart(indicatorName, data) {
    const chart = indicatorCharts[indicatorName];
    if (!chart) return;
    
    const labels = data.map(item => new Date(item.timestamp));
    const values = data.map(item => item[indicatorName]);
    
    chart.data.labels = labels;
    chart.data.datasets[0].data = values;
    chart.update();
}

// Get a color for an indicator based on its name
function getIndicatorColor(indicatorName) {
    const colors = {
        'rsi': 'rgba(75, 192, 192, 1)',
        'macd': 'rgba(153, 102, 255, 1)',
        'signal': 'rgba(255, 159, 64, 1)',
        'histogram': 'rgba(201, 203, 207, 1)',
        'sma': 'rgba(54, 162, 235, 1)',
        'ema': 'rgba(255, 99, 132, 1)',
        'bb_upper': 'rgba(75, 192, 192, 1)',
        'bb_middle': 'rgba(54, 162, 235, 1)',
        'bb_lower': 'rgba(255, 99, 132, 1)',
        'stoch_k': 'rgba(255, 206, 86, 1)',
        'stoch_d': 'rgba(153, 102, 255, 1)',
        'adx': 'rgba(255, 159, 64, 1)',
        'atr': 'rgba(255, 99, 132, 1)',
        'obv': 'rgba(54, 162, 235, 1)'
    };
    
    // Extract base indicator name
    const baseName = indicatorName.split('_')[0];
    
    return colors[indicatorName] || colors[baseName] || 'rgba(255, 255, 255, 0.7)';
}

// Create a chart for backtesting results
function createBacktestChart(containerId, backtestData) {
    const ctx = document.getElementById(containerId).getContext('2d');
    
    // Extract equity curve data
    const labels = Array.from({ length: backtestData.equity_curve.length }, (_, i) => i);
    const equityData = backtestData.equity_curve;
    const drawdownData = backtestData.drawdown_curve;
    
    const chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Equity Curve',
                    data: equityData,
                    borderColor: 'rgba(75, 192, 192, 1)',
                    tension: 0.1,
                    yAxisID: 'y'
                },
                {
                    label: 'Drawdown %',
                    data: drawdownData,
                    borderColor: 'rgba(255, 99, 132, 1)',
                    tension: 0.1,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: 'rgba(255, 255, 255, 0.7)'
                    }
                },
                y: {
                    position: 'left',
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: 'rgba(255, 255, 255, 0.7)'
                    }
                },
                y1: {
                    position: 'right',
                    grid: {
                        drawOnChartArea: false
                    },
                    ticks: {
                        color: 'rgba(255, 99, 132, 0.7)',
                        callback: function(value) {
                            return value + '%';
                        }
                    }
                }
            },
            plugins: {
                legend: {
                    labels: {
                        color: 'rgba(255, 255, 255, 0.7)'
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.datasetIndex === 1) {
                                label += context.parsed.y.toFixed(2) + '%';
                            } else {
                                label += context.parsed.y.toFixed(2);
                            }
                            return label;
                        }
                    }
                }
            }
        }
    });
    
    return chart;
}

// Create chart showing trade distribution
function createTradeDistributionChart(containerId, trades) {
    const ctx = document.getElementById(containerId).getContext('2d');
    
    // Count winning and losing trades by pair
    const pairStats = {};
    trades.forEach(trade => {
        const pair = trade.trading_pair;
        if (!pairStats[pair]) {
            pairStats[pair] = { winning: 0, losing: 0 };
        }
        
        if (trade.pnl > 0) {
            pairStats[pair].winning++;
        } else {
            pairStats[pair].losing++;
        }
    });
    
    // Prepare data for chart
    const pairs = Object.keys(pairStats);
    const winningTrades = pairs.map(pair => pairStats[pair].winning);
    const losingTrades = pairs.map(pair => pairStats[pair].losing);
    
    const chart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: pairs,
            datasets: [
                {
                    label: 'Winning Trades',
                    data: winningTrades,
                    backgroundColor: 'rgba(75, 192, 192, 0.7)'
                },
                {
                    label: 'Losing Trades',
                    data: losingTrades,
                    backgroundColor: 'rgba(255, 99, 132, 0.7)'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: 'rgba(255, 255, 255, 0.7)'
                    }
                },
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        precision: 0,
                        color: 'rgba(255, 255, 255, 0.7)'
                    }
                }
            },
            plugins: {
                legend: {
                    labels: {
                        color: 'rgba(255, 255, 255, 0.7)'
                    }
                }
            }
        }
    });
    
    return chart;
}

// Create performance metrics chart
function createPerformanceMetricsChart(containerId, metrics) {
    const ctx = document.getElementById(containerId).getContext('2d');
    
    const chart = new Chart(ctx, {
        type: 'radar',
        data: {
            labels: [
                'Win Rate',
                'Profit Factor',
                'Sharpe Ratio',
                'Recovery Factor',
                'Risk-Reward Ratio'
            ],
            datasets: [{
                label: 'Strategy Performance',
                data: [
                    metrics.win_rate * 100,  // Convert to percentage
                    Math.min(metrics.profit_factor, 5),  // Cap at 5 for visualization
                    Math.max(0, metrics.sharpe_ratio),  // Ensure positive
                    Math.max(0, metrics.return_pct / Math.max(metrics.max_drawdown_pct, 0.01)),  // Recovery factor
                    metrics.avg_profit / Math.max(metrics.avg_loss, 0.01)  // Risk-reward ratio
                ],
                fill: true,
                backgroundColor: 'rgba(54, 162, 235, 0.2)',
                borderColor: 'rgba(54, 162, 235, 1)',
                pointBackgroundColor: 'rgba(54, 162, 235, 1)',
                pointBorderColor: '#fff',
                pointHoverBackgroundColor: '#fff',
                pointHoverBorderColor: 'rgba(54, 162, 235, 1)'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                r: {
                    angleLines: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    pointLabels: {
                        color: 'rgba(255, 255, 255, 0.7)'
                    },
                    ticks: {
                        backdropColor: 'transparent',
                        color: 'rgba(255, 255, 255, 0.7)'
                    }
                }
            },
            plugins: {
                legend: {
                    labels: {
                        color: 'rgba(255, 255, 255, 0.7)'
                    }
                }
            }
        }
    });
    
    return chart;
}

// Create portfolio allocation chart
function createPortfolioAllocationChart(containerId, exposureData) {
    const ctx = document.getElementById(containerId).getContext('2d');
    
    // Extract data
    const pairs = Object.keys(exposureData.pair_exposure || {});
    const values = pairs.map(pair => exposureData.pair_exposure[pair]);
    
    const chart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: pairs,
            datasets: [{
                data: values,
                backgroundColor: [
                    'rgba(255, 99, 132, 0.7)',
                    'rgba(54, 162, 235, 0.7)',
                    'rgba(255, 206, 86, 0.7)',
                    'rgba(75, 192, 192, 0.7)',
                    'rgba(153, 102, 255, 0.7)',
                    'rgba(255, 159, 64, 0.7)',
                    'rgba(199, 199, 199, 0.7)',
                    'rgba(83, 102, 255, 0.7)',
                    'rgba(40, 159, 64, 0.7)',
                    'rgba(210, 99, 132, 0.7)'
                ],
                borderColor: [
                    'rgba(255, 99, 132, 1)',
                    'rgba(54, 162, 235, 1)',
                    'rgba(255, 206, 86, 1)',
                    'rgba(75, 192, 192, 1)',
                    'rgba(153, 102, 255, 1)',
                    'rgba(255, 159, 64, 1)',
                    'rgba(199, 199, 199, 1)',
                    'rgba(83, 102, 255, 1)',
                    'rgba(40, 159, 64, 1)',
                    'rgba(210, 99, 132, 1)'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        color: 'rgba(255, 255, 255, 0.7)'
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const value = context.raw;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(2) + '%';
                            return `${context.label}: ${value.toFixed(2)} (${percentage})`;
                        }
                    }
                }
            }
        }
    });
    
    return chart;
}

// Create the asset class exposure chart
function createAssetClassChart(containerId, exposureData) {
    const ctx = document.getElementById(containerId).getContext('2d');
    
    const data = {
        labels: ['Forex', 'Crypto', 'Cash'],
        datasets: [{
            data: [
                exposureData.forex_exposure || 0,
                exposureData.crypto_exposure || 0,
                exposureData.total_account_value - (exposureData.forex_exposure || 0) - (exposureData.crypto_exposure || 0)
            ],
            backgroundColor: [
                'rgba(54, 162, 235, 0.7)',
                'rgba(255, 206, 86, 0.7)',
                'rgba(75, 192, 192, 0.7)'
            ],
            borderColor: [
                'rgba(54, 162, 235, 1)',
                'rgba(255, 206, 86, 1)',
                'rgba(75, 192, 192, 1)'
            ],
            borderWidth: 1
        }]
    };
    
    const chart = new Chart(ctx, {
        type: 'doughnut',
        data: data,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        color: 'rgba(255, 255, 255, 0.7)'
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const value = context.raw;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(2) + '%';
                            return `${context.label}: ${value.toFixed(2)} (${percentage})`;
                        }
                    }
                }
            }
        }
    });
    
    return chart;
}
