-- CreateTable
CREATE TABLE "options" (
    "id" SERIAL NOT NULL,
    "ticker" TEXT NOT NULL,
    "underlying_ticker" TEXT NOT NULL,
    "contract_type" TEXT NOT NULL,
    "expiration_date" TIMESTAMPTZ NOT NULL,
    "strike_price" DOUBLE PRECISION NOT NULL,

    CONSTRAINT "options_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "option_snapshots" (
    "id" SERIAL NOT NULL,
    "optionId" INTEGER NOT NULL,
    "volume" DOUBLE PRECISION,
    "day_change" DOUBLE PRECISION,
    "day_close" DOUBLE PRECISION,
    "day_open" DOUBLE PRECISION,
    "implied_vol" DOUBLE PRECISION,
    "last_price" DOUBLE PRECISION,
    "last_updated" TIMESTAMPTZ,
    "last_crawled" TIMESTAMPTZ NOT NULL,
    "open_interest" INTEGER,

    CONSTRAINT "option_snapshots_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "options_ticker_key" ON "options"("ticker");

-- CreateIndex
CREATE INDEX "options_underlying_ticker_expiration_date_idx" ON "options"("underlying_ticker", "expiration_date");

-- CreateIndex
CREATE INDEX "options_strike_price_idx" ON "options"("strike_price");

-- CreateIndex
CREATE INDEX "option_snapshots_last_updated_idx" ON "option_snapshots"("last_updated");

-- CreateIndex
CREATE UNIQUE INDEX "option_snapshots_optionId_last_updated_key" ON "option_snapshots"("optionId", "last_updated");

-- AddForeignKey
ALTER TABLE "option_snapshots" ADD CONSTRAINT "option_snapshots_optionId_fkey" FOREIGN KEY ("optionId") REFERENCES "options"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
