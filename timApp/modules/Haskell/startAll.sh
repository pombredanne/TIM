#!/bin/bash

cd /Haskell/Choices
/hbin/ChoicesPlugin -p5001 &
/hbin/MultipleChoicesPlugin -p5002 &
/hbin/ShortNotePlugin -p5003 &
/hbin/GraphVizPlugin -p5004 

