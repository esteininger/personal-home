---
title: verification
date: "2026-10-30"
category: technology
description: the fields that race ahead share one trait: you can check an answer against a rule. a look at how to make more of the world verifiable, and why it all comes down to compute and energy.
---

some fields move fast and most of the world crawls. math, computer science, and parts of law race ahead while biology, medicine, and sales inch along. the difference comes down to one thing: whether you can check an answer.

## verifiable fields

math is verifiable by nature. you write a proof and a proof assistant like [lean](https://lean-lang.org) either accepts it or it does not. no committee, no decade-long wait for consensus. the proof holds or it fails, and you get a binding result the moment you hit enter.

computer science has the same shape. you write code and you run the tests, functional and unit and regression and ui. each test is a statement with a yes or no answer. the build comes back green or red.

law is more verifiable than it looks. tax code, property law, contracts. you make a claim against the rules and you get a binding outcome: a filing, a ruling, a settlement. the statement resolves into something real.

the common thread is a rule you can measure a statement against. issue a claim, get a verdict. when a field has that, progress compounds, because every attempt tells you something concrete about whether it worked.

## short loops

verification is half of it. speed is the other half.

the scientific method is one move repeated. you introduce a variable and you measure it against a baseline. an a/b test is the same move in a business suit. the faster you run that loop, the more experiments you fit into a day, and the more of the space you cover.

a field with slow feedback crawls even when its answers are checkable. a field with fast feedback compounds. put verifiability and short loops together and you get the flywheel that math and software have ridden for decades.

so the job for every other field is to build that same pair: a way to check a statement, and a loop short enough to run thousands of times.

## the rest of the world

this is the fun part. take biology, physics, and sales, and ask what their verifiable framework looks like.

biology already has one in places. a wet-lab assay gives a readout. the loop is slow and expensive, so the work is shortening it, with simulation, better instruments, and models that predict the assay before you run the real one.

sales feels fuzzy until you treat a message as a hypothesis. send it, measure the reply rate against a baseline, keep what wins. the rule is the market's response. the loop is as short as your sending cadence.

physics has theory you can test and simulation you can run against it. the lever is compute, so you run more of the experiment in silico before you touch the real world.

the move is the same every time. find the rule, build the check, shorten the loop.

## the upper bound

so what is the ceiling on all this? it is knowledge, and there is no ceiling. people keep reaching for the next secret of the universe, and there is always another one waiting. that is the beauty of being here. there is always something new to learn, and i think there always will be.

capitalism is the part that makes it move. it rewards the people who reach the edge of what is known and turn what they find into something other people can use. no cap on knowledge, and a prize for whoever pushes the frontier and brings something back.

## two levers

if knowledge is the goal and verifiable fields are the vehicle, then underneath everything there are only two levers: compute and energy.

running the models, running the experiments, running the verifications, that is compute. and compute runs on energy. everything else is detail stacked on top of those two.

so the real question is efficiency. more verification per unit of compute, more compute per unit of energy. squeeze either one and every verifiable field speeds up at once.

## why retrieval

this is where i get excited about retrieval, and why i am building [mixpeek](https://mixpeek.com).

an index is front-loaded compute. you pay the cost once, at the start, then spend the rest of the workflow collecting on it. say you have a million data points and a rough idea of the questions you will ask. you build the indexes up front, prepare the data once, and every downstream experiment runs cheap against work you already did.

the good version leaves room to move. you change the downstream questions without rebuilding the world each time. that flexibility is the whole point, and it is where clustering, fine-tuning, reinforcement learning, and online and offline learning come in. each one reuses the expensive work you already paid for and bends it toward a new use case.

that is the bet. pay for verification up front so it comes back cheap, keep the loop short, and let more of the world ride the flywheel that math and software already do.
