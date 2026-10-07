# V29 Structure

## User layer

`ReplyKeyboard` is reserved for the six primary areas only. Every area then opens a dedicated inline sub-menu.

`🏆 REYTING` intentionally contains only `TOP KITOBXONLAR`, `TOP REFERALLAR`, and `MENING O‘RNIM`.

## Admin layer

The admin surface has seven independent centers:

1. Dashboard
2. Content
3. Users
4. Rankings
5. Rewards
6. Channel
7. System

Cross-domain controls are kept out of the general settings screen. For example, referral settings live in Referral Center; ranking settings live in Rankings; reaction settings live in Channel.

## Data rules

- `points`: cumulative user points.
- `rank_points`: current visible TOP user score; can be reset independently.
- `referral_rank_score`: current visible TOP referral score; can be reset independently.
- confirmed referrals are kept separately from the public leaderboard score.

This lets an admin reset a leaderboard without erasing the user's long-term account history.
