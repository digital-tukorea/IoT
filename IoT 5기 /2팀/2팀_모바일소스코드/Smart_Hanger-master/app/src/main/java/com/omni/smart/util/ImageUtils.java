package com.omni.smart.util;

public class ImageUtils {
    private static final String SERVER_IP = "192.168.137.36";
    private static final String DOWNLOAD_URL_BASE = "http://" + SERVER_IP + ":8000/images/download/";

    public static String getFullUrl(String path) {
        if (path == null || path.isEmpty()) return null;
        
        android.util.Log.d("ImageUtils", "Original path: " + path);

        // Handle localhost/127.0.0.1 in URLs
        if (path.contains("localhost")) {
            String url = path.replace("localhost", SERVER_IP);
            android.util.Log.d("ImageUtils", "Replaced localhost: " + url);
            return url;
        }
        if (path.contains("127.0.0.1")) {
            String url = path.replace("127.0.0.1", SERVER_IP);
            android.util.Log.d("ImageUtils", "Replaced 127.0.0.1: " + url);
            return url;
        }

        // If it's already a full URL, return it
        if (path.startsWith("http://") || path.startsWith("https://")) {
            return path;
        }
        
        // Extract filename from server path (e.g., /home/.../qr_1.jpg -> qr_1.jpg)
        // Handle both forward and backward slashes
        String filename = path;
        int lastSlash = Math.max(path.lastIndexOf("/"), path.lastIndexOf("\\"));
        if (lastSlash != -1) {
            filename = path.substring(lastSlash + 1);
        }
        
        String url = DOWNLOAD_URL_BASE + filename;
        
        android.util.Log.d("ImageUtils", "Constructed Download URL: " + url);
        return url;
    }
}
