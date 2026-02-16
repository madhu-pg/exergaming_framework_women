import 'dart:math';
import 'package:flutter/material.dart';

double angleBetween(Offset a, Offset b) {
  final dot = a.dx * b.dx + a.dy * b.dy;
  final magA = a.distance;
  final magB = b.distance;

  final cosTheta = dot / (magA * magB);
  return acos(cosTheta.clamp(-1, 1)) * 180 / pi;
}
