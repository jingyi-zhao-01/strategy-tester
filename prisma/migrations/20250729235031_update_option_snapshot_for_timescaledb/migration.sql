/*
  Warnings:

  - A unique constraint covering the columns `[id,optionId,last_updated]` on the table `option_snapshots` will be added. If there are existing duplicate values, this will fail.
  - Made the column `last_updated` on table `option_snapshots` required. This step will fail if there are existing NULL values in that column.

*/
-- DropIndex
DROP INDEX "option_snapshots_optionId_last_updated_key";

-- AlterTable
ALTER TABLE "option_snapshots" ALTER COLUMN "last_updated" SET NOT NULL;

-- CreateIndex
CREATE UNIQUE INDEX "option_snapshots_id_optionId_last_updated_key" ON "option_snapshots"("id", "optionId", "last_updated");
