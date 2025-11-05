"""Initial schema

Revision ID: 001
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create runs table
    op.create_table(
        'runs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('mode', sa.Enum('backtest', 'paper', 'live', name='tradingmode'), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('stopped_at', sa.DateTime(), nullable=True),
        sa.Column('config_json', JSON(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('initial_capital', sa.Float(), nullable=False),
        sa.Column('final_capital', sa.Float(), nullable=True),
        sa.Column('total_pnl', sa.Float(), nullable=True),
        sa.Column('total_pnl_pct', sa.Float(), nullable=True),
        sa.Column('max_drawdown_pct', sa.Float(), nullable=True),
        sa.Column('win_rate', sa.Float(), nullable=True),
        sa.Column('total_trades', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_runs_mode'), 'runs', ['mode'], unique=False)

    # Create positions table
    op.create_table(
        'positions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('ts_open', sa.DateTime(), nullable=False),
        sa.Column('ts_close', sa.DateTime(), nullable=True),
        sa.Column('entry_price', sa.Float(), nullable=False),
        sa.Column('exit_price', sa.Float(), nullable=True),
        sa.Column('qty', sa.Float(), nullable=False),
        sa.Column('realized_pnl', sa.Float(), nullable=True),
        sa.Column('realized_pnl_pct', sa.Float(), nullable=True),
        sa.Column('status', sa.Enum('open', 'closed', name='positionstatus'), nullable=False),
        sa.Column('run_id', sa.Integer(), nullable=True),
        sa.Column('mode', sa.Enum('backtest', 'paper', 'live', name='tradingmode'), nullable=False),
        sa.Column('fees_paid', sa.Float(), nullable=False, default=0.0),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['run_id'], ['runs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_positions_status'), 'positions', ['status'], unique=False)
    op.create_index(op.f('ix_positions_ts_open'), 'positions', ['ts_open'], unique=False)
    op.create_index(op.f('ix_positions_run_id'), 'positions', ['run_id'], unique=False)

    # Create trades table
    op.create_table(
        'trades',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('ts', sa.DateTime(), nullable=False),
        sa.Column('side', sa.Enum('buy', 'sell', name='side'), nullable=False),
        sa.Column('qty', sa.Float(), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('fee', sa.Float(), nullable=False),
        sa.Column('fee_asset', sa.String(10), nullable=False),
        sa.Column('pnl', sa.Float(), nullable=True),
        sa.Column('run_id', sa.Integer(), nullable=True),
        sa.Column('mode', sa.Enum('backtest', 'paper', 'live', name='tradingmode'), nullable=False),
        sa.Column('position_id', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['position_id'], ['positions.id'], ),
        sa.ForeignKeyConstraint(['run_id'], ['runs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_trades_ts'), 'trades', ['ts'], unique=False)
    op.create_index(op.f('ix_trades_run_id'), 'trades', ['run_id'], unique=False)
    op.create_index(op.f('ix_trades_position_id'), 'trades', ['position_id'], unique=False)

    # Create orders table
    op.create_table(
        'orders',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('ts', sa.DateTime(), nullable=False),
        sa.Column('side', sa.Enum('buy', 'sell', name='side'), nullable=False),
        sa.Column('order_type', sa.Enum('market', 'limit', 'post_only', name='ordertype'), nullable=False),
        sa.Column('status', sa.Enum('pending', 'open', 'partially_filled', 'filled', 'cancelled', 'rejected', 'expired', name='orderstatus'), nullable=False),
        sa.Column('qty', sa.Float(), nullable=False),
        sa.Column('price', sa.Float(), nullable=True),
        sa.Column('filled_qty', sa.Float(), nullable=False, default=0.0),
        sa.Column('filled_price', sa.Float(), nullable=True),
        sa.Column('exchange_id', sa.String(100), nullable=True),
        sa.Column('reason', sa.String(200), nullable=True),
        sa.Column('run_id', sa.Integer(), nullable=True),
        sa.Column('mode', sa.Enum('backtest', 'paper', 'live', name='tradingmode'), nullable=False),
        sa.Column('idempotency_key', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['runs.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('idempotency_key')
    )
    op.create_index(op.f('ix_orders_ts'), 'orders', ['ts'], unique=False)
    op.create_index(op.f('ix_orders_status'), 'orders', ['status'], unique=False)
    op.create_index(op.f('ix_orders_run_id'), 'orders', ['run_id'], unique=False)

    # Create candles table
    op.create_table(
        'candles',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('symbol', sa.String(20), nullable=False),
        sa.Column('ts', sa.DateTime(), nullable=False),
        sa.Column('open', sa.Float(), nullable=False),
        sa.Column('high', sa.Float(), nullable=False),
        sa.Column('low', sa.Float(), nullable=False),
        sa.Column('close', sa.Float(), nullable=False),
        sa.Column('volume', sa.Float(), nullable=False),
        sa.Column('source', sa.String(50), nullable=False),
        sa.Column('timeframe', sa.String(10), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_candles_symbol'), 'candles', ['symbol'], unique=False)
    op.create_index(op.f('ix_candles_ts'), 'candles', ['ts'], unique=False)

    # Create state table
    op.create_table(
        'state',
        sa.Column('key', sa.String(100), nullable=False),
        sa.Column('value_json', JSON(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('key')
    )


def downgrade() -> None:
    op.drop_table('state')
    op.drop_table('candles')
    op.drop_index(op.f('ix_orders_run_id'), table_name='orders')
    op.drop_index(op.f('ix_orders_status'), table_name='orders')
    op.drop_index(op.f('ix_orders_ts'), table_name='orders')
    op.drop_table('orders')
    op.drop_index(op.f('ix_trades_position_id'), table_name='trades')
    op.drop_index(op.f('ix_trades_run_id'), table_name='trades')
    op.drop_index(op.f('ix_trades_ts'), table_name='trades')
    op.drop_table('trades')
    op.drop_index(op.f('ix_positions_run_id'), table_name='positions')
    op.drop_index(op.f('ix_positions_ts_open'), table_name='positions')
    op.drop_index(op.f('ix_positions_status'), table_name='positions')
    op.drop_table('positions')
    op.drop_index(op.f('ix_runs_mode'), table_name='runs')
    op.drop_table('runs')
