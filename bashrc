#!/usr/bin/env bash

# If not running interactively, don't do anything
case $- in
  *i*) ;;
    *) return;;
esac


export PATH=$PATH:~/bin:~/.local/bin:~/go/bin

# Load customizations
source ~/.bashrc.d/*
