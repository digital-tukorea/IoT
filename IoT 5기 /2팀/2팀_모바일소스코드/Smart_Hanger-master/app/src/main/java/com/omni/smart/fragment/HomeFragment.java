package com.omni.smart.fragment;

import android.content.ContentUris;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.provider.CalendarContract;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.fragment.app.Fragment;
import androidx.lifecycle.ViewModelProvider;
import androidx.recyclerview.widget.LinearLayoutManager;

import com.bumptech.glide.Glide;
import com.omni.smart.adapter.EventAdapter;
import com.omni.smart.adapter.ForecastAdapter;
import com.omni.smart.databinding.FragmentHomeBinding;
import com.omni.smart.helper.PermissionHelper;
import com.omni.smart.model.AqiData;
import com.omni.smart.model.CalendarEvent;
import com.omni.smart.model.ForecastItem;
import com.omni.smart.model.UserContext;
import com.omni.smart.model.WeatherData;
import com.omni.smart.util.CalendarHelper;
import com.omni.smart.viewmodel.HomeViewModel;

import java.util.List;
import java.util.stream.Collectors;

public class HomeFragment extends Fragment {
    private FragmentHomeBinding binding;
    private HomeViewModel viewModel;
    private ForecastAdapter adapter;
    private EventAdapter eventAdapter;

    @Nullable
    @Override
    public View onCreateView(@NonNull LayoutInflater inflater, @Nullable ViewGroup container, @Nullable Bundle savedInstanceState) {
        binding = FragmentHomeBinding.inflate(inflater, container, false);
        return binding.getRoot();

    }

    @Override
    public void onViewCreated(@NonNull View view, @Nullable Bundle savedInstanceState) {
        super.onViewCreated(view, savedInstanceState);
        viewModel = new ViewModelProvider(this).get(HomeViewModel.class);

        setupRecyclerView();
        observeViewModel();

        // UI-only addition: give the location header extra top padding equal to the
        // status bar height, since the app draws edge-to-edge and this header sits
        // directly over the photo background. Nothing else in the layout is affected.
        final int baseTopPadding = binding.llLocationHeader.getPaddingTop();
        androidx.core.view.ViewCompat.setOnApplyWindowInsetsListener(binding.getRoot(), (v, insets) -> {
            int statusBarInset = insets.getInsets(androidx.core.view.WindowInsetsCompat.Type.statusBars()).top;
            binding.llLocationHeader.setPadding(
                    binding.llLocationHeader.getPaddingLeft(),
                    baseTopPadding + statusBarInset,
                    binding.llLocationHeader.getPaddingRight(),
                    binding.llLocationHeader.getPaddingBottom());
            return insets;
        });

        binding.swipeRefresh.setOnRefreshListener(() -> {
            viewModel.refreshLocation();
            loadEvents();
        });

        binding.ivLogout.setOnClickListener(v -> {
            new androidx.appcompat.app.AlertDialog.Builder(requireContext())
                    .setTitle("로그아웃")
                    .setMessage("로그아웃 하시겠습니까?")
                    .setPositiveButton("로그아웃", (dialog, which) -> {
                        requireContext()
                                .getSharedPreferences("user_auth", android.content.Context.MODE_PRIVATE)
                                .edit()
                                .putBoolean("is_logged_in", false)
                                .apply();

                        Intent intent = new Intent(requireContext(), com.omni.smart.activity.LoginActivity.class);
                        intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TASK);
                        startActivity(intent);
                        requireActivity().finish();
                    })
                    .setNegativeButton("취소", null)
                    .show();
        });


        binding.btnAddEvent.setOnClickListener(v -> {
            long startMillis = System.currentTimeMillis();
            Uri.Builder builder = CalendarContract.CONTENT_URI.buildUpon();
            builder.appendPath("time");
            ContentUris.appendId(builder, startMillis);
            Intent intent = new Intent(Intent.ACTION_VIEW)
                    .setData(builder.build());
            startActivity(intent);
        });

        viewModel.refreshLocation();
        loadEvents();
    }

    @Override
    public void onResume() {
        super.onResume();
        // UI-only addition: if calendar permission was granted *after* onViewCreated
        // already ran once (e.g. user approved the system dialog), this makes sure
        // the schedule row and rvEvents catch up instead of staying stuck on the
        // default "일정이 없습니다" text.
        if (binding != null) {
            loadEvents();
        }
    }

    private void setupRecyclerView() {
        adapter = new ForecastAdapter();
        binding.rvForecast.setLayoutManager(new LinearLayoutManager(getContext(), LinearLayoutManager.HORIZONTAL, false));
        binding.rvForecast.setAdapter(adapter);

        eventAdapter = new EventAdapter();
        binding.rvEvents.setLayoutManager(new LinearLayoutManager(getContext()));
        binding.rvEvents.setAdapter(eventAdapter);
    }

    private void loadEvents() {
        if (PermissionHelper.hasPermissions(requireContext())) {
            List<CalendarEvent> events = CalendarHelper.getTodayEvents(requireContext());
            eventAdapter.setEventList(events);

            // UI-only addition: simple "오늘 일정 있음/없음" row, tap jumps to 캘린더 tab
            boolean hasEvents = events != null && !events.isEmpty();
            binding.tvScheduleStatus.setText(hasEvents ? "오늘 예정된 일정이 있습니다." : "오늘 예정된 일정이 없습니다.");
            binding.llScheduleRow.setOnClickListener(v -> {
                if (getActivity() instanceof com.omni.smart.activity.MainActivity) {
                    ((com.omni.smart.activity.MainActivity) getActivity()).selectCalendarTab();
                }
            });

            // Sync with server once events are loaded and weather is available
            triggerServerSync();
        }
    }

    private void triggerServerSync() {
        WeatherData weather = viewModel.getCurrentWeather().getValue();
        AqiData aqi = viewModel.getAirPollution().getValue();
        List<com.omni.smart.model.CalendarEvent> events = CalendarHelper.getTodayEvents(requireContext());

        String status = "free";
        List<UserContext.ScheduleItem> scheduleItems = new java.util.ArrayList<>();

        if (events != null && !events.isEmpty()) {
            status = "busy";
            for (com.omni.smart.model.CalendarEvent event : events) {
                scheduleItems.add(new UserContext.ScheduleItem(
                        String.valueOf(event.getStartTime()),
                        event.getTitle()
                ));
            }
        }

        if (weather != null && aqi != null) {
            viewModel.syncContextToServer(weather, aqi, status, scheduleItems);
        }
    }

    // UI-only helper: turn the raw OpenWeatherMap condition word (English) into
    // the Korean sentence + emoji shown under the temperature, e.g.
    // "오늘 하늘은 구름 많음 ☁️ 입니다."
    private String buildConditionSentence(String condition) {
        String lower = condition != null ? condition.toLowerCase() : "";
        String kor;
        String emoji;
        switch (lower) {
            case "clear":
                kor = "맑음";
                emoji = "☀️";
                break;
            case "clouds":
                kor = "구름 많음";
                emoji = "☁️";
                break;
            case "rain":
                kor = "비";
                emoji = "🌧️";
                break;
            case "drizzle":
                kor = "이슬비";
                emoji = "🌦️";
                break;
            case "thunderstorm":
                kor = "천둥번개";
                emoji = "⛈️";
                break;
            case "snow":
                kor = "눈";
                emoji = "❄️";
                break;
            case "mist":
            case "fog":
            case "haze":
                kor = "안개";
                emoji = "🌫️";
                break;
            default:
                kor = condition != null ? condition : "알 수 없음";
                emoji = "🌤️";
        }
        return "오늘 하늘은 " + kor + " " + emoji + " 입니다.";
    }

    // UI-only helper: 한국 환경부 기준 미세먼지/초미세먼지 등급 텍스트 + 이모지
    private String pmGradeText(double value, boolean isPm10) {
        int good = isPm10 ? 30 : 15;
        int normal = isPm10 ? 80 : 35;
        int bad = isPm10 ? 150 : 75;

        if (value <= good) return "좋음 😀";
        if (value <= normal) return "보통 🙂";
        if (value <= bad) return "나쁨 😷";
        return "매우나쁨 🤢";
    }

    private void observeViewModel() {
        viewModel.getAddress().observe(getViewLifecycleOwner(), addr -> {
            binding.tvLocation.setText(addr);
        });

        viewModel.getCurrentWeather().observe(getViewLifecycleOwner(), weatherData -> {
            binding.swipeRefresh.setRefreshing(false);
            if (weatherData != null) {
                binding.tvMainTemp.setText(Math.round(weatherData.getTemp()) + "°");
                binding.tvCondition.setText(buildConditionSentence(weatherData.getCondition()));
                binding.tvHumidity.setText(weatherData.getHumidity() + "%");
                binding.tvFeelsLike.setText(Math.round(weatherData.getFeelsLike()) + "°");
                binding.tvWindSpeed.setText(String.format("%.1f m/s", weatherData.getWindSpeed()));

                // UI-only addition: pick the background photo that matches the current
                // condition. Uses the condition string that was already fetched above;
                // no new data source, network call, or business logic is introduced.
                String conditionLower = weatherData.getCondition() != null ? weatherData.getCondition().toLowerCase() : "";
                boolean isRainyLook = conditionLower.contains("rain") || conditionLower.contains("drizzle")
                        || conditionLower.contains("thunderstorm") || conditionLower.contains("snow");
                binding.ivWeatherBackground.setImageResource(isRainyLook ? com.omni.smart.R.drawable.bg_weather_rain : com.omni.smart.R.drawable.bg_weather_sun);

                String iconUrl = "https://openweathermap.org/img/wn/" + weatherData.getIcon() + "@4x.png";
                Glide.with(this).load(iconUrl).into(binding.ivMainWeatherIcon);

                triggerServerSync();
            }
        });

        viewModel.getForecast().observe(getViewLifecycleOwner(), forecastResponse -> {
            if (forecastResponse != null && forecastResponse.getList() != null) {
                List<ForecastItem> items = forecastResponse.getList();
                adapter.setForecastList(items.stream().limit(8).collect(Collectors.toList()));

                if (!items.isEmpty()) {
                    binding.tvRainProb.setText(items.get(0).getPopPercent() + "%");
                }
            }
        });

        viewModel.getAirPollution().observe(getViewLifecycleOwner(), aqiData -> {
            if (aqiData != null) {
                binding.tvPm10Grade.setText(pmGradeText(aqiData.getPm10(), true));
                binding.tvPm25Grade.setText(pmGradeText(aqiData.getPm25(), false));
                triggerServerSync();
            }
        });

        viewModel.getSyncStatus().observe(getViewLifecycleOwner(), success -> {
            if (success != null && success) {
                // Optionally show a small indicator or log
                android.util.Log.d("HomeFragment", "Context synced to server successfully");
            }
        });
    }

    @Override
    public void onDestroyView() {
        super.onDestroyView();
        binding = null;
    }
}