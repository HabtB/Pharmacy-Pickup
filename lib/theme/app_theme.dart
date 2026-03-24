import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Centralized brand colors used across the entire app.
class AppColors {
  AppColors._();

  // Brand
  static const Color msBlue       = Color(0xFF005596);
  static const Color msMagenta    = Color(0xFFD80B8C);

  // Primary palette derived from brand
  static const Color primary      = msBlue;
  static const Color primaryLight = Color(0xFF3378AB);
  static const Color primaryDark  = Color(0xFF003A6B);

  // Accent
  static const Color accent       = msMagenta;
  static const Color accentLight  = Color(0xFFE85AAF);

  // Semantic
  static const Color success      = Color(0xFF2E7D32);
  static const Color successLight = Color(0xFFE8F5E9);
  static const Color caution      = Color(0xFFF9A825);
  static const Color cautionLight = Color(0xFFFFF8E1);
  static const Color danger       = Color(0xFFD32F2F);
  static const Color dangerLight  = Color(0xFFFFEBEE);

  // Neutrals
  static const Color surface      = Color(0xFFF8F9FA);
  static const Color cardBg       = Colors.white;
  static const Color textPrimary  = Color(0xFF1A1A2E);
  static const Color textSecondary = Color(0xFF6C757D);
  static const Color divider      = Color(0xFFE0E0E0);

  // Location-type colors (for medication zones)
  static const Color ivColor      = Color(0xFFB71C1C);
  static const Color fridgeColor  = Color(0xFF00838F);
  static const Color storeColor   = Color(0xFF4E342E);
}

/// Build the app-wide [ThemeData] used in MaterialApp.
ThemeData buildAppTheme() {
  final base = ThemeData(
    useMaterial3: true,
    colorScheme: ColorScheme.fromSeed(
      seedColor: AppColors.msBlue,
      primary: AppColors.msBlue,
      secondary: AppColors.msMagenta,
      surface: AppColors.surface,
      error: AppColors.danger,
    ),
  );

  return base.copyWith(
    scaffoldBackgroundColor: AppColors.surface,

    // AppBar
    appBarTheme: AppBarTheme(
      backgroundColor: AppColors.msBlue,
      foregroundColor: Colors.white,
      elevation: 0,
      centerTitle: false,
      titleTextStyle: GoogleFonts.inter(
        fontSize: 18,
        fontWeight: FontWeight.w600,
        color: Colors.white,
      ),
    ),

    // Cards
    cardTheme: CardThemeData(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      color: AppColors.cardBg,
      surfaceTintColor: Colors.transparent,
    ),

    // Elevated Buttons
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: AppColors.msBlue,
        foregroundColor: Colors.white,
        elevation: 0,
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        textStyle: GoogleFonts.inter(
          fontSize: 16,
          fontWeight: FontWeight.w600,
        ),
      ),
    ),

    // Text Theme
    textTheme: GoogleFonts.interTextTheme(base.textTheme).copyWith(
      headlineLarge: GoogleFonts.inter(
        fontSize: 28,
        fontWeight: FontWeight.w800,
        color: AppColors.textPrimary,
      ),
      headlineMedium: GoogleFonts.inter(
        fontSize: 22,
        fontWeight: FontWeight.w700,
        color: AppColors.textPrimary,
      ),
      titleLarge: GoogleFonts.inter(
        fontSize: 18,
        fontWeight: FontWeight.w600,
        color: AppColors.textPrimary,
      ),
      bodyLarge: GoogleFonts.inter(
        fontSize: 16,
        fontWeight: FontWeight.w400,
        color: AppColors.textPrimary,
      ),
      bodyMedium: GoogleFonts.inter(
        fontSize: 14,
        fontWeight: FontWeight.w400,
        color: AppColors.textSecondary,
      ),
      labelLarge: GoogleFonts.inter(
        fontSize: 14,
        fontWeight: FontWeight.w600,
        letterSpacing: 0.5,
      ),
    ),

    // Input fields
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: Colors.grey.shade50,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: BorderSide.none,
      ),
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
    ),

    // TabBar
    tabBarTheme: TabBarThemeData(
      labelColor: Colors.white,
      unselectedLabelColor: Colors.white70,
      indicatorColor: AppColors.msMagenta,
      indicatorSize: TabBarIndicatorSize.tab,
    ),

    // Divider
    dividerTheme: const DividerThemeData(
      color: AppColors.divider,
      thickness: 1,
    ),

    // SnackBar
    snackBarTheme: SnackBarThemeData(
      behavior: SnackBarBehavior.floating,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
    ),
  );
}
