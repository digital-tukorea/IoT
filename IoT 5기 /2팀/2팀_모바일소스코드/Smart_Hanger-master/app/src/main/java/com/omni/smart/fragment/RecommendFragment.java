package com.omni.smart.fragment;

import android.os.Bundle;
import android.util.Log;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.fragment.app.Fragment;
import androidx.lifecycle.ViewModelProvider;
import androidx.recyclerview.widget.LinearLayoutManager;

import com.omni.smart.adapter.RecommendAdapter;
import com.omni.smart.databinding.FragmentRecommendBinding;
import com.omni.smart.model.AqiData;
import com.omni.smart.model.CalendarEvent;
import com.omni.smart.model.UserContext;
import com.omni.smart.model.WeatherData;
import com.omni.smart.mqtt.MqttHelper;
import com.omni.smart.util.CalendarHelper;
import com.omni.smart.viewmodel.HomeViewModel;
import com.omni.smart.viewmodel.RecommendViewModel;

import org.eclipse.paho.client.mqttv3.IMqttActionListener;
import org.eclipse.paho.client.mqttv3.IMqttToken;

import java.util.ArrayList;
import java.util.List;

public class RecommendFragment extends Fragment {
    private static final String TAG = "RecommendFragment";
    private FragmentRecommendBinding binding;
    private RecommendViewModel viewModel;
    private HomeViewModel homeViewModel;
    private RecommendAdapter adapter;
    private MqttHelper mqttHelper;

    @Nullable
    @Override
    public View onCreateView(@NonNull LayoutInflater inflater, @Nullable ViewGroup container, @Nullable Bundle savedInstanceState) {
        binding = FragmentRecommendBinding.inflate(inflater, container, false);
        return binding.getRoot();
    }

    @Override
    public void onViewCreated(@NonNull View view, @Nullable Bundle savedInstanceState) {
        super.onViewCreated(view, savedInstanceState);
        viewModel = new ViewModelProvider(this).get(RecommendViewModel.class);
        homeViewModel = new ViewModelProvider(requireActivity()).get(HomeViewModel.class);

        mqttHelper = new MqttHelper(requireContext());
        connectMqtt();

        setupRecyclerView();
        observeViewModel();

        binding.btnRefresh.setOnClickListener(v -> getRecommendations(false));

        // UI-only addition: reuse the already-loaded weather condition (via the existing
        // shared homeViewModel field) purely to choose which blurred background photo to
        // show, same approach as ClosetFragment. No new network/business logic added.
        homeViewModel.getCurrentWeather().observe(getViewLifecycleOwner(), weatherDataForBg -> {
            if (weatherDataForBg != null) {
                String conditionLower = weatherDataForBg.getCondition() != null ? weatherDataForBg.getCondition().toLowerCase() : "";
                boolean isRainyLook = conditionLower.contains("rain") || conditionLower.contains("drizzle")
                        || conditionLower.contains("thunderstorm") || conditionLower.contains("snow");
                binding.ivRecommendBackground.setImageResource(isRainyLook
                        ? com.omni.smart.R.drawable.bg_closet_rain_blur
                        : com.omni.smart.R.drawable.bg_closet_sun_blur);
            }
        });

        // UI-only addition: try fetching immediately when the tab opens (in addition to
        // the existing weather-triggered auto-fetch below), so results don't require an
        // extra button tap. getRecommendations() already guards against duplicate/parallel
        // requests via viewModel.getIsLoading(), so this is safe to call eagerly.
        getRecommendations(true);
    }

    private void connectMqtt() {
        mqttHelper.connect(new IMqttActionListener() {
            @Override
            public void onSuccess(IMqttToken asyncActionToken) {
                Log.d(TAG, "MQTT Connected");
            }

            @Override
            public void onFailure(IMqttToken asyncActionToken, Throwable exception) {
                Log.e(TAG, "MQTT Connection Failed: " + exception.getMessage());
            }
        });
    }

    private void setupRecyclerView() {
        adapter = new RecommendAdapter(clothing -> {
            sendClothingToHanger(clothing);
        });
        binding.rvRecommendations.setLayoutManager(new LinearLayoutManager(getContext()));
        binding.rvRecommendations.setAdapter(adapter);
    }

    private void sendClothingToHanger(com.omni.smart.model.Clothing clothing) {
        String message = "{\"id\":\"" + clothing.getId() + "\"}";
        if (mqttHelper.isConnected()) {
            mqttHelper.publish(message);
            Toast.makeText(getContext(), "Sending " + clothing.getName() + "...", Toast.LENGTH_SHORT).show();
        } else {
            Toast.makeText(getContext(), "Connecting to Hanger...", Toast.LENGTH_SHORT).show();
            mqttHelper.connect(new IMqttActionListener() {
                @Override
                public void onSuccess(IMqttToken asyncActionToken) {
                    mqttHelper.publish(message);
                    if (getActivity() != null) {
                        getActivity().runOnUiThread(() ->
                                Toast.makeText(getContext(), "Connected! Sending " + clothing.getName(), Toast.LENGTH_SHORT).show()
                        );
                    }
                }

                @Override
                public void onFailure(IMqttToken asyncActionToken, Throwable exception) {
                    if (getActivity() != null) {
                        getActivity().runOnUiThread(() ->
                                Toast.makeText(getContext(), "Hanger connection failed.", Toast.LENGTH_SHORT).show()
                        );
                    }
                }
            });
        }
    }

    private void getRecommendations(boolean clearExclusions) {
        if (Boolean.TRUE.equals(viewModel.getIsLoading().getValue())) return;

        WeatherData weather = homeViewModel.getCurrentWeather().getValue();
        AqiData aqi = homeViewModel.getAirPollution().getValue();
        List<CalendarEvent> events = CalendarHelper.getTodayEvents(requireContext());

        UserContext context = new UserContext();
        if (homeViewModel.getLocation().getValue() != null) {
            context.setLatitude(homeViewModel.getLocation().getValue().getLatitude());
            context.setLongitude(homeViewModel.getLocation().getValue().getLongitude());
        }

        if (weather != null) {
            context.setWeather(weather.getCondition());
        }

        if (aqi != null) {
            context.setAqi(aqi.getAqi());
        }

        List<UserContext.ScheduleItem> scheduleItems = new ArrayList<>();
        if (!events.isEmpty()) {
            context.setScheduleStatus("busy");
            for (CalendarEvent event : events) {
                scheduleItems.add(new UserContext.ScheduleItem(
                        String.valueOf(event.getStartTime()),
                        event.getTitle()
                ));
            }
        } else {
            context.setScheduleStatus("free");
        }
        context.setSchedule(scheduleItems);

        viewModel.fetchRecommendations(context, clearExclusions);
    }

    private void observeViewModel() {
        viewModel.getRecommendations().observe(getViewLifecycleOwner(), list -> {
            adapter.submitList(list);
        });

        viewModel.getIsLoading().observe(getViewLifecycleOwner(), loading -> {
            binding.progressBar.setVisibility(loading ? View.VISIBLE : View.GONE);
            binding.btnRefresh.setEnabled(!loading);
        });

        viewModel.getStatusMessage().observe(getViewLifecycleOwner(), message -> {
            if (message != null) {
                Toast.makeText(getContext(), message, Toast.LENGTH_SHORT).show();
            }
        });

        // Trigger recommendation once weather data is available if not already loaded
        homeViewModel.getCurrentWeather().observe(getViewLifecycleOwner(), weather -> {
            if (weather != null && (viewModel.getRecommendations().getValue() == null || viewModel.getRecommendations().getValue().isEmpty())) {
                getRecommendations(true);
            }
        });
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        if (mqttHelper != null) {
            mqttHelper.disconnect();
        }
    }

    @Override
    public void onDestroyView() {
        super.onDestroyView();
        binding = null;
    }
}