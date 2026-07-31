// WebSocket functionality for real-time data

let websocket = null;
let marketDataSubscriptions = [];

// Initialize WebSocket connection
function initWebSocket(callback) {
    // Check if WebSocket is already connected
    if (websocket && websocket.readyState === WebSocket.OPEN) {
        return;
    }
    
    // Determine appropriate WebSocket URL
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    
    // Create new WebSocket connection
    websocket = new WebSocket(wsUrl);
    
    // Set up WebSocket event handlers
    websocket.onopen = function(e) {
        console.log('WebSocket connection established');
        
        // Resubscribe to previous subscriptions if any
        if (marketDataSubscriptions.length > 0) {
            marketDataSubscriptions.forEach(subscription => {
                subscribeToPair(subscription.pair, subscription.timeframe);
            });
        }
        
        if (typeof callback === 'function') {
            callback(true);
        }
    };
    
    websocket.onmessage = function(e) {
        try {
            const data = JSON.parse(e.data);
            handleWebSocketMessage(data);
        } catch (error) {
            console.error('Error parsing WebSocket message:', error);
        }
    };
    
    websocket.onclose = function(e) {
        console.log('WebSocket connection closed:', e.code, e.reason);
        websocket = null;
        
        // Attempt to reconnect after a delay
        setTimeout(() => {
            initWebSocket(callback);
        }, 5000);
    };
    
    websocket.onerror = function(e) {
        console.error('WebSocket error:', e);
        if (typeof callback === 'function') {
            callback(false, 'WebSocket connection error');
        }
    };
}

// Handle incoming WebSocket messages
function handleWebSocketMessage(data) {
    if (!data || !data.type) return;
    
    switch (data.type) {
        case 'price_update':
            // Update price data in real-time
            updateRealTimePrices(data.data);
            break;
            
        case 'candle_update':
            // Update chart with new candle
            updateChartWithCandle(data.data);
            break;
            
        case 'signal':
            // Display new trading signal
            showNewSignal(data.data);
            break;
            
        case 'trade_execution':
            // Display trade execution
            showTradeExecution(data.data);
            break;
            
        case 'error':
            // Display error message
            console.error('WebSocket error:', data.message);
            break;
            
        default:
            console.log('Unknown message type:', data.type);
    }
}

// Subscribe to price updates for a trading pair
function subscribeToPair(pair, timeframe) {
    if (!websocket || websocket.readyState !== WebSocket.OPEN) {
        // If WebSocket is not open, initialize it and subscribe when open
        initWebSocket(() => {
            subscribeToPair(pair, timeframe);
        });
        return;
    }
    
    // Send subscription message
    const subscription = {
        action: 'subscribe',
        pair: pair,
        timeframe: timeframe || '1m'
    };
    
    websocket.send(JSON.stringify(subscription));
    
    // Add to subscriptions list if not already present
    const existingSubscription = marketDataSubscriptions.find(
        sub => sub.pair === pair && sub.timeframe === (timeframe || '1m')
    );
    
    if (!existingSubscription) {
        marketDataSubscriptions.push({
            pair: pair,
            timeframe: timeframe || '1m'
        });
    }
    
    console.log(`Subscribed to ${pair} (${timeframe || '1m'}) updates`);
}

// Unsubscribe from price updates for a trading pair
function unsubscribeFromPair(pair, timeframe) {
    if (!websocket || websocket.readyState !== WebSocket.OPEN) {
        return;
    }
    
    // Send unsubscription message
    const unsubscription = {
        action: 'unsubscribe',
        pair: pair,
        timeframe: timeframe || '1m'
    };
    
    websocket.send(JSON.stringify(unsubscription));
    
    // Remove from subscriptions list
    marketDataSubscriptions = marketDataSubscriptions.filter(
        sub => !(sub.pair === pair && sub.timeframe === (timeframe || '1m'))
    );
    
    console.log(`Unsubscribed from ${pair} (${timeframe || '1m'}) updates`);
}

// Update real-time prices on the UI
function updateRealTimePrices(priceData) {
    if (!priceData || !priceData.pair || !priceData.price) return;
    
    // Update price elements with matching pair
    const priceElements = document.querySelectorAll('.price-current[data-pair="' + priceData.pair + '"]');
    
    priceElements.forEach(element => {
        const currentPrice = parseFloat(element.textContent);
        const newPrice = priceData.price;
        
        // Update price
        element.textContent = newPrice.toFixed(newPrice >= 100 ? 2 : 6);
        
        // Add class for price movement animation
        if (currentPrice > newPrice) {
            element.classList.remove('price-up');
            element.classList.add('price-down');
        } else if (currentPrice < newPrice) {
            element.classList.remove('price-down');
            element.classList.add('price-up');
        }
        
        // Remove classes after animation
        setTimeout(() => {
            element.classList.remove('price-up', 'price-down');
        }, 1000);
    });
    
    // Update mini ticker elements if they exist
    const tickerElements = document.querySelectorAll('.mini-ticker[data-pair="' + priceData.pair + '"]');
    
    tickerElements.forEach(element => {
        const priceElement = element.querySelector('.ticker-price');
        if (priceElement) {
            const currentPrice = parseFloat(priceElement.textContent);
            const newPrice = priceData.price;
            
            // Update price
            priceElement.textContent = newPrice.toFixed(newPrice >= 100 ? 2 : 6);
            
            // Update price movement indication
            if (currentPrice > newPrice) {
                element.classList.remove('ticker-up');
                element.classList.add('ticker-down');
            } else if (currentPrice < newPrice) {
                element.classList.remove('ticker-down');
                element.classList.add('ticker-up');
            }
        }
    });
}

// Update chart with new candle data
function updateChartWithCandle(candleData) {
    if (!candleData || !candleData.pair || !candleData.timeframe) return;
    
    // Check if we have an active chart that matches this pair and timeframe
    if (priceChart && 
        activePair === candleData.pair && 
        activeTimeframe === candleData.timeframe) {
        
        // Convert candleData to chart format
        const candle = {
            x: new Date(candleData.timestamp),
            o: candleData.open,
            h: candleData.high,
            l: candleData.low,
            c: candleData.close
        };
        
        // Find if candle with same timestamp already exists
        const existingCandleIndex = priceChart.data.datasets[0].data.findIndex(
            c => c.x.getTime() === candle.x.getTime()
        );
        
        if (existingCandleIndex !== -1) {
            // Update existing candle
            priceChart.data.datasets[0].data[existingCandleIndex] = candle;
        } else {
            // Add new candle
            priceChart.data.datasets[0].data.push(candle);
            
            // Remove oldest candle if we're maintaining a fixed number of candles
            if (priceChart.data.datasets[0].data.length > MAX_CANDLES) {
                priceChart.data.datasets[0].data.shift();
            }
        }
        
        // Update chart
        priceChart.update();
        
        // If we have indicator charts, update them too
        updateIndicatorChartsWithNewData(candleData);
    }
}

// Update indicator charts with new data
function updateIndicatorChartsWithNewData(candleData) {
    // For each indicator chart we're displaying
    Object.keys(indicatorCharts).forEach(indicatorName => {
        const chart = indicatorCharts[indicatorName];
        
        // Find the latest data point time
        const lastPointTime = chart.data.labels.length > 0 ? 
            chart.data.labels[chart.data.labels.length - 1].getTime() : 0;
        
        // If this candle's time matches our latest point or is newer
        if (candleData.timestamp >= lastPointTime) {
            // We need to calculate the indicator value for this new candle
            // This would typically be done on the server side and sent with the candle data
            // For now, we'll just use a placeholder approach
            
            // If the indicator value is included in the candle data
            if (candleData.indicators && candleData.indicators[indicatorName] !== undefined) {
                const newValue = candleData.indicators[indicatorName];
                
                if (lastPointTime === candleData.timestamp) {
                    // Update existing point
                    const lastIndex = chart.data.labels.length - 1;
                    chart.data.datasets[0].data[lastIndex] = newValue;
                } else {
                    // Add new point
                    chart.data.labels.push(new Date(candleData.timestamp));
                    chart.data.datasets[0].data.push(newValue);
                    
                    // Remove oldest point if we're maintaining a fixed number of points
                    if (chart.data.labels.length > MAX_CANDLES) {
                        chart.data.labels.shift();
                        chart.data.datasets[0].data.shift();
                    }
                }
                
                // Update chart
                chart.update();
            }
        }
    });
}

// Show a new trading signal
function showNewSignal(signalData) {
    // Check if notifications are enabled
    if (!('Notification' in window)) {
        console.log('This browser does not support desktop notification');
        return;
    }
    
    // Create notification content
    const title = `${signalData.signal_type} Signal: ${signalData.trading_pair}`;
    const options = {
        body: `Entry: ${signalData.entry_price.toFixed(6)}, Stop Loss: ${signalData.stop_loss.toFixed(6)}, Take Profit: ${signalData.take_profit.toFixed(6)}`,
        icon: '/static/img/logo.png'
    };
    
    // Request permission and show notification
    if (Notification.permission === 'granted') {
        const notification = new Notification(title, options);
    } else if (Notification.permission !== 'denied') {
        Notification.requestPermission().then(permission => {
            if (permission === 'granted') {
                const notification = new Notification(title, options);
            }
        });
    }
    
    // Also show a toast notification
    showToastNotification(title, options.body, 'success');
    
    // Refresh signals list if on dashboard
    if (window.location.pathname === '/dashboard') {
        fetchRecentSignals();
    }
}

// Show a trade execution notification
function showTradeExecution(tradeData) {
    const title = `Trade Executed: ${tradeData.order_type} ${tradeData.trading_pair}`;
    const body = `Price: ${tradeData.price.toFixed(6)}, Amount: ${tradeData.amount.toFixed(4)}`;
    
    // Show toast notification
    showToastNotification(title, body, 'info');
    
    // Refresh active positions and recent trades if on dashboard
    if (window.location.pathname === '/dashboard') {
        fetchActivePositions();
        fetchRecentTrades();
    }
}

// Show a toast notification
function showToastNotification(title, message, type = 'info') {
    // Create notification container if it doesn't exist
    let toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }
    
    // Create a unique ID for the toast
    const toastId = 'toast-' + Date.now();
    
    // Create toast element
    const toastHtml = `
        <div id="${toastId}" class="toast" role="alert" aria-live="assertive" aria-atomic="true">
            <div class="toast-header">
                <strong class="me-auto">${title}</strong>
                <small>${new Date().toLocaleTimeString()}</small>
                <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        </div>
    `;
    
    // Add toast to container
    toastContainer.innerHTML += toastHtml;
    
    // Initialize the toast
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, {
        autohide: true,
        delay: 5000
    });
    
    // Show the toast
    toast.show();
    
    // Remove the toast element after it's hidden
    toastElement.addEventListener('hidden.bs.toast', function() {
        toastElement.remove();
    });
}

// Close WebSocket connection
function closeWebSocket() {
    if (websocket) {
        websocket.close();
        websocket = null;
        marketDataSubscriptions = [];
    }
}

// When page is unloaded, close WebSocket
window.addEventListener('beforeunload', closeWebSocket);
