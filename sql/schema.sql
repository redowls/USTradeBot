-- USTradeBot — SQL Server schema (Phase 6: persistence).
--
-- Idempotent: every object is created only if it does not already exist, so this
-- script doubles as the runtime bootstrap (bot.persistence.TradeStore.ensure_schema
-- runs it on startup) and a hand-runnable SSMS script. Batches are separated by a
-- lone `GO`; the runtime splits on it (pyodbc cannot send `GO` itself).
--
-- Model: the bot opens one position per watchlist symbol and closes it as a single
-- round-trip, so `dbo.trades` is the analytical core — one row per trade carrying
-- the entry, the confidence breakdown that sized it, the exit, and realized P/L.
-- `dbo.orders` is an append-only audit log of submissions; `dbo.positions` mirrors
-- the currently-open holdings; `dbo.fills` is reserved for the broker trade-updates
-- stream (real fill prices / partials) that lands in a later phase.

-- One row per round-trip trade (entry -> exit). The analytical core.
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'trades' AND schema_id = SCHEMA_ID('dbo'))
CREATE TABLE dbo.trades (
    id                INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
    symbol            VARCHAR(16)    NOT NULL,
    model             CHAR(1)        NOT NULL,                 -- sizing model: A | B
    status            VARCHAR(8)     NOT NULL DEFAULT 'OPEN',  -- OPEN | CLOSED
    entry_order_id    VARCHAR(64)    NULL,                     -- Alpaca bracket order id
    entry_time_utc    DATETIME2(0)   NOT NULL DEFAULT SYSUTCDATETIME(),
    entry_price       DECIMAL(18, 6) NOT NULL,
    qty               INT            NOT NULL,
    notional          DECIMAL(18, 4) NOT NULL,
    stop_price        DECIMAL(18, 6) NOT NULL,
    target_price      DECIMAL(18, 6) NOT NULL,
    confidence        DECIMAL(6, 2)  NOT NULL,                 -- total 0-100
    conf_crossover    DECIMAL(5, 4)  NULL,                     -- sub-scores 0-1
    conf_trend        DECIMAL(5, 4)  NULL,
    conf_rsi          DECIMAL(5, 4)  NULL,
    conf_volume       DECIMAL(5, 4)  NULL,
    conf_volatility   DECIMAL(5, 4)  NULL,
    exit_order_id     VARCHAR(64)    NULL,
    exit_time_utc     DATETIME2(0)   NULL,
    exit_price        DECIMAL(18, 6) NULL,
    exit_reason       VARCHAR(64)    NULL,
    pnl               DECIMAL(18, 4) NULL,                     -- realized $ at exit
    pnl_pct           DECIMAL(9, 4)  NULL,
    created_at_utc    DATETIME2(0)   NOT NULL DEFAULT SYSUTCDATETIME(),
    updated_at_utc    DATETIME2(0)   NOT NULL DEFAULT SYSUTCDATETIME()
);
GO

-- Fast lookup of the single open trade per symbol (the exit-update predicate).
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_trades_symbol_status' AND object_id = OBJECT_ID('dbo.trades'))
CREATE INDEX IX_trades_symbol_status ON dbo.trades (symbol, status);
GO

-- Append-only audit log of every order the bot submits (entry brackets + exits).
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'orders' AND schema_id = SCHEMA_ID('dbo'))
CREATE TABLE dbo.orders (
    id                INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
    trade_id          INT            NULL,                     -- -> dbo.trades.id
    alpaca_order_id   VARCHAR(64)    NULL,
    symbol            VARCHAR(16)    NOT NULL,
    side              VARCHAR(4)     NOT NULL,                 -- BUY | SELL
    role              VARCHAR(8)     NOT NULL,                 -- ENTRY | EXIT
    qty               INT            NULL,
    order_type        VARCHAR(16)    NOT NULL,                 -- BRACKET | CLOSE
    limit_price       DECIMAL(18, 6) NULL,
    stop_price        DECIMAL(18, 6) NULL,
    status            VARCHAR(16)    NULL,
    confidence        DECIMAL(6, 2)  NULL,
    submitted_at_utc  DATETIME2(0)   NOT NULL DEFAULT SYSUTCDATETIME()
);
GO

-- Currently-open positions: one row per held symbol (inserted on entry, removed on exit).
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'positions' AND schema_id = SCHEMA_ID('dbo'))
CREATE TABLE dbo.positions (
    symbol         VARCHAR(16)    NOT NULL PRIMARY KEY,
    trade_id       INT            NULL,                        -- -> dbo.trades.id
    qty            INT            NOT NULL,
    entry_price    DECIMAL(18, 6) NOT NULL,
    stop_price     DECIMAL(18, 6) NULL,
    target_price   DECIMAL(18, 6) NULL,
    opened_at_utc  DATETIME2(0)   NOT NULL DEFAULT SYSUTCDATETIME()
);
GO

-- Reserved for the broker trade-updates stream (real fill prices / partial fills).
-- Created now so the schema is complete; populated in a later phase.
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'fills' AND schema_id = SCHEMA_ID('dbo'))
CREATE TABLE dbo.fills (
    id               INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
    trade_id         INT            NULL,                      -- -> dbo.trades.id
    alpaca_order_id  VARCHAR(64)    NULL,
    symbol           VARCHAR(16)    NOT NULL,
    side             VARCHAR(4)     NOT NULL,
    qty              INT            NOT NULL,
    fill_price       DECIMAL(18, 6) NOT NULL,
    filled_at_utc    DATETIME2(0)   NOT NULL DEFAULT SYSUTCDATETIME()
);
GO

-- Outcome vs confidence: does a higher confidence score actually pay off? Buckets
-- closed trades into confidence bands and aggregates win rate and realized P/L.
CREATE OR ALTER VIEW dbo.vw_confidence_outcome AS
SELECT
    CASE
        WHEN confidence >= 90 THEN '90-100'
        WHEN confidence >= 80 THEN '80-89'
        WHEN confidence >= 70 THEN '70-79'
        WHEN confidence >= 60 THEN '60-69'
        ELSE '<60'
    END                                                            AS confidence_band,
    COUNT(*)                                                       AS trades,
    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END)                       AS wins,
    CAST(AVG(CASE WHEN pnl > 0 THEN 1.0 ELSE 0.0 END) AS DECIMAL(5, 4)) AS win_rate,
    CAST(AVG(pnl) AS DECIMAL(18, 4))                               AS avg_pnl,
    CAST(SUM(pnl) AS DECIMAL(18, 4))                               AS total_pnl,
    CAST(AVG(pnl_pct) AS DECIMAL(9, 4))                            AS avg_pnl_pct
FROM dbo.trades
WHERE status = 'CLOSED' AND pnl IS NOT NULL
GROUP BY
    CASE
        WHEN confidence >= 90 THEN '90-100'
        WHEN confidence >= 80 THEN '80-89'
        WHEN confidence >= 70 THEN '70-79'
        WHEN confidence >= 60 THEN '60-69'
        ELSE '<60'
    END;
GO
