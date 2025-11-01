"""Real-time Plotly Dash dashboard for arbitrage monitoring."""
import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
from datetime import datetime, timedelta
import pandas as pd
from collections import deque
from loguru import logger


class ArbitrageDashboard:
    """Real-time dashboard for monitoring arbitrage opportunities."""

    def __init__(self, detector, ml_predictor=None):
        self.detector = detector
        self.ml_predictor = ml_predictor

        # Initialize Dash app with Bootstrap theme
        self.app = dash.Dash(
            __name__,
            external_stylesheets=[dbc.themes.CYBORG],
            title="Crypto Arbitrage Monitor"
        )

        # Data storage for time series
        self.price_history = {
            'BTC-USD': deque(maxlen=200),
            'ETH-USD': deque(maxlen=200),
            'SOL-USD': deque(maxlen=200)
        }

        self.opportunity_history = deque(maxlen=100)

        # Setup layout
        self._setup_layout()
        self._setup_callbacks()

    def _setup_layout(self):
        """Create dashboard layout."""
        self.app.layout = dbc.Container([
            # Header
            dbc.Row([
                dbc.Col([
                    html.H1("🚀 Crypto Arbitrage Monitor", className="text-center mb-4"),
                    html.P(
                        "Real-time arbitrage detection across Coinbase, Binance, and Bitstamp",
                        className="text-center text-muted"
                    )
                ])
            ]),

            html.Hr(),

            # Statistics Cards
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("Total Opportunities", className="card-title"),
                            html.H2(id="total-opps", children="0", className="text-success")
                        ])
                    ], color="dark", outline=True)
                ], width=3),

                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("Avg Profit", className="card-title"),
                            html.H2(id="avg-profit", children="0.00%", className="text-info")
                        ])
                    ], color="dark", outline=True)
                ], width=3),

                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("Max Profit", className="card-title"),
                            html.H2(id="max-profit", children="0.00%", className="text-warning")
                        ])
                    ], color="dark", outline=True)
                ], width=3),

                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("Recent (5min)", className="card-title"),
                            html.H2(id="recent-count", children="0", className="text-danger")
                        ])
                    ], color="dark", outline=True)
                ], width=3),
            ], className="mb-4"),

            # Best Current Opportunity Alert
            dbc.Row([
                dbc.Col([
                    html.Div(id="best-opportunity-alert")
                ])
            ], className="mb-4"),

            # Live Price Charts
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("📈 Live Price Feeds"),
                        dbc.CardBody([
                            dcc.Graph(id="price-chart", config={'displayModeBar': False})
                        ])
                    ], color="dark")
                ])
            ], className="mb-4"),

            # Opportunities Table
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("💰 Recent Arbitrage Opportunities"),
                        dbc.CardBody([
                            html.Div(id="opportunities-table")
                        ])
                    ], color="dark")
                ], width=8),

                # Spread Heatmap
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("🔥 Spread Heatmap"),
                        dbc.CardBody([
                            dcc.Graph(id="spread-heatmap", config={'displayModeBar': False})
                        ])
                    ], color="dark")
                ], width=4),
            ], className="mb-4"),

            # ML Predictions (if available)
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("🤖 ML Spread Predictions"),
                        dbc.CardBody([
                            html.Div(id="ml-predictions")
                        ])
                    ], color="dark")
                ])
            ], className="mb-4"),

            # Backtest Results
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("📊 Backtest Performance"),
                        dbc.CardBody([
                            html.Div(id="backtest-results")
                        ])
                    ], color="dark")
                ])
            ]),

            # Auto-refresh interval
            dcc.Interval(
                id='interval-component',
                interval=1000,  # Update every 1 second
                n_intervals=0
            )

        ], fluid=True, className="p-4")

    def _setup_callbacks(self):
        """Setup dashboard callbacks."""

        @self.app.callback(
            [
                Output("total-opps", "children"),
                Output("avg-profit", "children"),
                Output("max-profit", "children"),
                Output("recent-count", "children"),
            ],
            Input("interval-component", "n_intervals")
        )
        def update_stats(n):
            stats = self.detector.get_statistics()

            return (
                f"{stats['total_opportunities']:,}",
                f"{stats['avg_profit']:.2f}%",
                f"{stats['max_profit']:.2f}%",
                str(stats['recent_count'])
            )

        @self.app.callback(
            Output("best-opportunity-alert", "children"),
            Input("interval-component", "n_intervals")
        )
        def update_best_opportunity(n):
            best = self.detector.get_best_opportunity()

            if not best:
                return dbc.Alert(
                    "⏳ Monitoring exchanges... No opportunities detected yet.",
                    color="secondary"
                )

            return dbc.Alert([
                html.H4("🎯 BEST OPPORTUNITY", className="alert-heading"),
                html.Hr(),
                html.P([
                    html.Strong(f"{best.symbol}: "),
                    f"Buy on {best.buy_exchange} @ ${best.buy_price:.2f} → ",
                    f"Sell on {best.sell_exchange} @ ${best.sell_price:.2f}"
                ]),
                html.P([
                    html.Strong("Profit after fees: "),
                    html.Span(f"{best.profit_after_fees:.2f}%", className="text-success fs-4"),
                    f" (spread: {best.spread_pct:.2f}%)"
                ]),
                html.Small(f"Detected: {best.timestamp.strftime('%H:%M:%S')}")
            ], color="success", className="mb-0")

        @self.app.callback(
            Output("price-chart", "figure"),
            Input("interval-component", "n_intervals")
        )
        def update_price_chart(n):
            fig = go.Figure()

            symbols = ['BTC-USD', 'ETH-USD', 'SOL-USD']
            colors = {'Coinbase': '#0052FF', 'Binance': '#F3BA2F', 'Bitstamp': '#00D43A'}

            for symbol in symbols:
                # Get latest prices for this symbol
                prices = self.detector.get_latest_prices(symbol)

                for exchange, price_data in prices.items():
                    # Store in history
                    if symbol not in self.price_history:
                        self.price_history[symbol] = deque(maxlen=200)

                    self.price_history[symbol].append({
                        'timestamp': price_data.timestamp,
                        'exchange': exchange,
                        'price': price_data.price
                    })

            # Plot each symbol
            for symbol in symbols:
                if symbol in self.price_history and len(self.price_history[symbol]) > 0:
                    df = pd.DataFrame(list(self.price_history[symbol]))

                    for exchange in df['exchange'].unique():
                        ex_df = df[df['exchange'] == exchange]

                        fig.add_trace(go.Scatter(
                            x=ex_df['timestamp'],
                            y=ex_df['price'],
                            mode='lines',
                            name=f"{symbol} - {exchange}",
                            line=dict(color=colors.get(exchange, '#FFFFFF'), width=2),
                            hovertemplate=f"<b>{exchange}</b><br>" +
                                        "Price: $%{y:.2f}<br>" +
                                        "<extra></extra>"
                        ))

            fig.update_layout(
                template="plotly_dark",
                height=400,
                xaxis_title="Time",
                yaxis_title="Price (USD)",
                hovermode='x unified',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )

            return fig

        @self.app.callback(
            Output("opportunities-table", "children"),
            Input("interval-component", "n_intervals")
        )
        def update_opportunities_table(n):
            recent_opps = self.detector.get_recent_opportunities(minutes=5)

            if not recent_opps:
                return html.P("No opportunities detected yet...", className="text-muted")

            # Sort by profit
            recent_opps = sorted(
                recent_opps,
                key=lambda x: x.profit_after_fees,
                reverse=True
            )[:20]  # Top 20

            table_header = [
                html.Thead(html.Tr([
                    html.Th("Time"),
                    html.Th("Symbol"),
                    html.Th("Buy"),
                    html.Th("Sell"),
                    html.Th("Spread"),
                    html.Th("Profit"),
                ]))
            ]

            rows = []
            for opp in recent_opps:
                rows.append(html.Tr([
                    html.Td(opp.timestamp.strftime("%H:%M:%S")),
                    html.Td(opp.symbol),
                    html.Td(f"{opp.buy_exchange} ${opp.buy_price:.2f}"),
                    html.Td(f"{opp.sell_exchange} ${opp.sell_price:.2f}"),
                    html.Td(f"{opp.spread_pct:.2f}%"),
                    html.Td(
                        f"{opp.profit_after_fees:.2f}%",
                        className="text-success fw-bold"
                    ),
                ]))

            table_body = [html.Tbody(rows)]

            return dbc.Table(
                table_header + table_body,
                bordered=True,
                hover=True,
                responsive=True,
                striped=True,
                className="mb-0"
            )

        @self.app.callback(
            Output("spread-heatmap", "figure"),
            Input("interval-component", "n_intervals")
        )
        def update_spread_heatmap(n):
            """Create heatmap of spreads between exchanges."""
            symbols = ['BTC-USD', 'ETH-USD', 'SOL-USD']
            exchanges = ['Coinbase', 'Binance', 'Bitstamp']

            # Calculate current spreads
            spread_matrix = []

            for symbol in symbols:
                spreads = self.detector.calculate_spread_metrics(symbol)
                row = []

                for ex1 in exchanges:
                    for ex2 in exchanges:
                        if ex1 == ex2:
                            row.append(0)
                        else:
                            key = f"{ex1}->{ex2}"
                            if key in spreads:
                                row.append(spreads[key].get('current', 0))
                            else:
                                row.append(0)
                spread_matrix.append(row)

            fig = go.Figure(data=go.Heatmap(
                z=spread_matrix,
                x=exchanges * len(exchanges),
                y=symbols,
                colorscale='RdYlGn',
                zmid=0,
                text=[[f"{val:.2f}%" for val in row] for row in spread_matrix],
                texttemplate="%{text}",
                textfont={"size": 10},
                hovertemplate="<b>%{y}</b><br>Spread: %{z:.2f}%<extra></extra>"
            ))

            fig.update_layout(
                template="plotly_dark",
                height=300,
                xaxis_title="Exchange",
                yaxis_title="Symbol"
            )

            return fig

        @self.app.callback(
            Output("ml-predictions", "children"),
            Input("interval-component", "n_intervals")
        )
        def update_ml_predictions(n):
            if not self.ml_predictor or not self.ml_predictor.is_trained:
                return html.P(
                    "⚙️ ML model training in progress... (need ~5 min of data)",
                    className="text-muted"
                )

            predictions = []
            symbols = ['BTC-USD', 'ETH-USD', 'SOL-USD']

            for symbol in symbols:
                df = self.detector.get_historical_data(symbol)
                if not df.empty:
                    pred = self.ml_predictor.predict_spread(df)
                    if pred is not None:
                        predictions.append(
                            dbc.ListGroupItem([
                                html.Strong(f"{symbol}: "),
                                f"Predicted spread in 30s: ",
                                html.Span(
                                    f"{pred:.2f}%",
                                    className="text-success" if pred > 0.5 else "text-danger"
                                )
                            ])
                        )

            if not predictions:
                return html.P("No predictions available yet...", className="text-muted")

            return dbc.ListGroup(predictions)

        @self.app.callback(
            Output("backtest-results", "children"),
            Input("interval-component", "n_intervals")
        )
        def update_backtest_results(n):
            """Run backtest on recent opportunities."""
            from arbitrage_detector import BacktestEngine

            backtest = BacktestEngine(initial_capital=10000)
            recent_opps = self.detector.get_recent_opportunities(minutes=60)

            for opp in recent_opps:
                backtest.execute_opportunity(opp)

            results = backtest.get_results()

            if results['total_trades'] == 0:
                return html.P("No trades to backtest yet...", className="text-muted")

            return dbc.Row([
                dbc.Col([
                    html.P([
                        html.Strong("Total Trades: "),
                        str(results['total_trades'])
                    ]),
                    html.P([
                        html.Strong("Win Rate: "),
                        f"{results['win_rate']:.1f}%"
                    ]),
                ]),
                dbc.Col([
                    html.P([
                        html.Strong("Total Return: "),
                        html.Span(
                            f"${results['total_return']:.2f} ({results['total_return_pct']:.2f}%)",
                            className="text-success" if results['total_return'] > 0 else "text-danger"
                        )
                    ]),
                    html.P([
                        html.Strong("Avg Profit/Trade: "),
                        f"${results['avg_profit_per_trade']:.2f}"
                    ]),
                ]),
            ])

    def run(self, host='0.0.0.0', port=8050, debug=False):
        """Start the dashboard server."""
        logger.info(f"Starting dashboard on http://{host}:{port}")
        self.app.run(host=host, port=port, debug=debug)
