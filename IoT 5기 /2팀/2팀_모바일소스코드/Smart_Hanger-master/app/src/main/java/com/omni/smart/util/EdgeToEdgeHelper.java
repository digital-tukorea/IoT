package com.omni.smart.util;

import android.view.View;
import android.view.Window;

import androidx.core.view.WindowCompat;
import androidx.core.view.WindowInsetsControllerCompat;

public class EdgeToEdgeHelper {
    public static void enable(Window window) {
        WindowCompat.setDecorFitsSystemWindows(window, false);
        
        // Optional: Ensure status bar and nav bar icons are light (for dark theme)
        WindowInsetsControllerCompat controller = WindowCompat.getInsetsController(window, window.getDecorView());
        if (controller != null) {
            controller.setAppearanceLightStatusBars(false);
            controller.setAppearanceLightNavigationBars(false);
        }
    }
}
