import 'package:flutter/material.dart';

class NativeCameraPreview extends StatelessWidget {
  const NativeCameraPreview({super.key});

  @override
  Widget build(BuildContext context) {
    return const SizedBox.expand(
      child: AndroidView(
        viewType: 'camera_preview_view',
        layoutDirection: TextDirection.ltr,
      ),
    );
  }
}
