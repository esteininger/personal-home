---
title: encoders
date: "2025-12-21"
description: "most people think AI understands language the way we do. it doesn't. it converts words into numbers and does math on them."
---

# how sentence encoders actually work

most people think AI understands language the way we do. it doesn't. it converts words into numbers and does math on them.

here's how that actually works.

## turning words into vectors

a sentence encoder takes your text and outputs a list of numbers—usually 384 to 1024 of them. this list is called an embedding or vector.

each number represents some learned feature of meaning. not features humans designed, but patterns the model discovered by reading billions of sentences during training.

<iframe src="/images/posts/sentence-encoder-animation.html" width="100%" height="300" frameborder="0" style="border: none; background: transparent;"></iframe>

## why this matters for search

the magic is that similar meanings land close together in this number space.

"the dog ran quickly" and "a fast-running canine" produce vectors that are mathematically close, even though they share zero words. "the dog ran quickly" and "quarterly earnings report" are far apart.

this is how semantic search works. you encode the query, encode your documents, then find the nearest neighbors.

<iframe src="/images/posts/sentence-encoder-animation.html" width="100%" height="300" frameborder="0" style="border: none; background: transparent;"></iframe>

## what's happening inside

the encoder is usually a transformer model. your sentence gets tokenized into subword pieces, then passes through multiple layers of attention.

attention lets each token look at every other token and decide what's relevant. "bank" near "river" attends differently than "bank" near "account."

the final layer pools all this context into one fixed-size vector representing the whole sentence.

<iframe src="/images/posts/transformer-encoder-animation.html" width="100%" height="300" frameborder="0" style="border: none; background: transparent;"></iframe>

## the tradeoffs

bigger models capture more nuance but cost more to run. smaller models are faster but miss subtlety.

domain matters too. an encoder trained on legal documents will outperform a general one for legal search, even if it's smaller.

there's no universal best—just the right fit for your data and latency budget.
